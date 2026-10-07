"""Tests for subscription state machine service (T002)."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database import SessionLocal, init_db, drop_db, Base
from src.models.entities import Organization, Subscription
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.services.subscription_service import SubscriptionService, SubscriptionStateError


@pytest.fixture
def db():
    """Create a test database session."""
    drop_db()
    init_db()
    db = SessionLocal()
    yield db
    db.close()
    drop_db()


@pytest.fixture
def org(db: Session):
    """Create a test organization."""
    org = Organization(name="Test Org", code="TEST")
    db.add(org)
    db.commit()
    return org


@pytest.fixture
def subscription_monthly(db: Session, org: Organization):
    """Create a monthly subscription."""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    grace_end = tomorrow + timedelta(days=7)
    sub = Subscription(
        organization_id=org.id,
        plan="BASIC",
        term=SubscriptionTerm.MONTHLY.value,
        state=SubscriptionState.ACTIVE.value,
        start_date=datetime.utcnow(),
        expiry_date=tomorrow,
        grace_end_date=grace_end,
    )
    db.add(sub)
    db.commit()
    return sub


@pytest.fixture
def subscription_annual(db: Session, org: Organization):
    """Create an annual subscription."""
    tomorrow = datetime.utcnow() + timedelta(days=1)
    grace_end = tomorrow + timedelta(days=30)
    sub = Subscription(
        organization_id=org.id,
        plan="PROFESSIONAL",
        term=SubscriptionTerm.ANNUAL.value,
        state=SubscriptionState.ACTIVE.value,
        start_date=datetime.utcnow(),
        expiry_date=tomorrow,
        grace_end_date=grace_end,
    )
    db.add(sub)
    db.commit()
    return sub


class TestSubscriptionStateComputation:
    """Test subscription state machine computation."""

    def test_active_subscription(self, subscription_monthly):
        """Test that future-dated subscription is ACTIVE."""
        state = SubscriptionService.compute_current_state(subscription_monthly)
        assert state == SubscriptionState.ACTIVE

    def test_expired_in_grace(self, db, org):
        """Test that expired subscription within grace period is in GRACE."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=6)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.GRACE.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=yesterday,
            grace_end_date=tomorrow,
        )
        db.add(sub)
        db.commit()

        state = SubscriptionService.compute_current_state(sub)
        assert state == SubscriptionState.GRACE

    def test_grace_expired_is_limited(self, db, org):
        """Test that grace-expired subscription is LIMITED."""
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.LIMITED.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow() - timedelta(days=9),
            grace_end_date=two_days_ago,
        )
        db.add(sub)
        db.commit()

        state = SubscriptionService.compute_current_state(sub)
        assert state == SubscriptionState.LIMITED


class TestGracePeriodComputation:
    """Test grace period duration computation."""

    def test_monthly_grace_is_7_days(self):
        """Test that monthly subscriptions get 7 day grace."""
        now = datetime.utcnow()
        grace_end = SubscriptionService.compute_grace_end_date(now, SubscriptionTerm.MONTHLY)
        delta = grace_end - now
        assert delta.days == 7

    def test_annual_grace_is_30_days(self):
        """Test that annual subscriptions get 30 day grace."""
        now = datetime.utcnow()
        grace_end = SubscriptionService.compute_grace_end_date(now, SubscriptionTerm.ANNUAL)
        delta = grace_end - now
        assert delta.days == 30

    def test_invalid_term_raises(self):
        """Test that invalid term raises error."""
        with pytest.raises(SubscriptionStateError):
            SubscriptionService.compute_grace_end_date(
                datetime.utcnow(),
                "INVALID",
            )


class TestStateTransitions:
    """Test subscription state transitions."""

    def test_transition_to_grace_on_expiry(self, db, org):
        """Test transition to GRACE when expiry reached."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=6)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.ACTIVE.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=yesterday,
            grace_end_date=tomorrow,
        )
        db.add(sub)
        db.commit()

        result = SubscriptionService.transition_to_grace_if_expired(sub, db)
        assert result is True
        assert sub.state == SubscriptionState.GRACE.value

    def test_transition_to_limited_on_grace_expiry(self, db, org):
        """Test transition to LIMITED when grace expires."""
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.GRACE.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow() - timedelta(days=9),
            grace_end_date=two_days_ago,
        )
        db.add(sub)
        db.commit()

        result = SubscriptionService.transition_to_limited_if_grace_expired(sub, db)
        assert result is True
        assert sub.state == SubscriptionState.LIMITED.value


class TestOperationalChecks:
    """Test operational status checks."""

    def test_active_is_operational(self, subscription_monthly):
        """Test that ACTIVE subscriptions are operational."""
        assert SubscriptionService.is_operational(subscription_monthly) is True

    def test_grace_is_operational(self, db, org):
        """Test that GRACE subscriptions are operational."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=6)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.GRACE.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=yesterday,
            grace_end_date=tomorrow,
        )
        db.add(sub)
        db.commit()

        assert SubscriptionService.is_operational(sub) is True

    def test_limited_is_not_operational(self, db, org):
        """Test that LIMITED subscriptions are not operational."""
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.LIMITED.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow() - timedelta(days=9),
            grace_end_date=two_days_ago,
        )
        db.add(sub)
        db.commit()

        assert SubscriptionService.is_operational(sub) is False


class TestRenewal:
    """Test subscription renewal."""

    def test_renewal_resets_to_active(self, db, org):
        """Test that renewal resets subscription to ACTIVE."""
        old_sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.LIMITED.value,
            start_date=datetime.utcnow() - timedelta(days=40),
            expiry_date=datetime.utcnow() - timedelta(days=8),
            grace_end_date=datetime.utcnow() - timedelta(days=1),
        )
        db.add(old_sub)
        db.commit()

        new_expiry = datetime.utcnow() + timedelta(days=30)
        SubscriptionService.renew_subscription(old_sub, new_expiry, db)

        assert old_sub.state == SubscriptionState.ACTIVE.value
        assert old_sub.expiry_date == new_expiry
        assert old_sub.grace_end_date is not None

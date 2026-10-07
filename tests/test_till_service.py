"""Tests for till session and limited mode service."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.entities import TillSession
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.services.till_service import TillService
from src.services.subscription_service import SubscriptionService


class TestTillSessionLifecycle:
    """Test till session operations."""

    def test_open_session(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test opening a till session."""
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            opening_balance=100.00,
            db=db,
        )

        assert session.status == "OPEN"
        assert session.opening_balance == 100.00
        assert session.operator_id == user.id

    def test_close_session(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test closing a till session."""
        # Open
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            opening_balance=100.00,
            db=db,
        )

        # Close
        closed = TillService.close_session(
            till_session_id=session.id,
            closing_balance=150.00,
            notes="Good day",
            db=db,
        )

        assert closed.status == "CLOSED"
        assert closed.closing_balance == 150.00
        assert closed.closed_at is not None

    def test_cannot_open_while_open(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test that opening till twice fails."""
        # Open first session
        TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            db=db,
        )

        # Try to open second session (should fail)
        with pytest.raises(ValueError, match="already has an open session"):
            TillService.open_session(
                organization_id=org.id,
                till_id=till.id,
                operator_id=user.id,
                db=db,
            )

    def test_get_current_open_session(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test fetching current open session."""
        # No open session
        session = TillService.get_current_open_session(till.id, db)
        assert session is None

        # Open session
        opened = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            db=db,
        )

        # Fetch it
        fetched = TillService.get_current_open_session(till.id, db)
        assert fetched is not None
        assert fetched.id == opened.id


class TestLimitedModeEnforcement:
    """Test subscription limited mode restrictions."""

    def test_cannot_open_when_limited(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test that opening till fails when subscription is LIMITED."""
        # Create LIMITED subscription
        yesterday = datetime.utcnow() - timedelta(days=2)
        from src.models.entities import Subscription
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.LIMITED.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow() - timedelta(days=9),
            grace_end_date=yesterday,
        )
        db.add(sub)
        db.commit()

        # Try to open till (should fail)
        with pytest.raises(ValueError, match="LIMITED mode"):
            TillService.assert_open_allowed(org.id, db)

    def test_can_open_when_active(
        self,
        db: Session,
        org,
        till,
        user,
        subscription_active,
    ):
        """Test that opening till succeeds when subscription is ACTIVE."""
        # Should not raise
        TillService.assert_open_allowed(org.id, db)

        # Should be able to open
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            db=db,
        )

        assert session.status == "OPEN"

    def test_can_open_when_grace(
        self,
        db: Session,
        org,
        till,
        user,
    ):
        """Test that opening till succeeds when subscription is GRACE."""
        # Create GRACE subscription
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=6)
        from src.models.entities import Subscription
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

        # Should not raise
        TillService.assert_open_allowed(org.id, db)

        # Should be able to open
        session = TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            db=db,
        )

        assert session.status == "OPEN"


class TestOfflineCachedState:
    """Test offline cached subscription state checks."""

    def test_allow_with_cached_active(self):
        """Test that ACTIVE cached state allows operation."""
        # Should not raise
        TillService.assert_offline_cached_allowed(SubscriptionState.ACTIVE.value)

    def test_allow_with_cached_grace(self):
        """Test that GRACE cached state allows operation."""
        # Should not raise
        TillService.assert_offline_cached_allowed(SubscriptionState.GRACE.value)

    def test_block_with_cached_limited(self):
        """Test that LIMITED cached state blocks operation."""
        with pytest.raises(ValueError, match="LIMITED"):
            TillService.assert_offline_cached_allowed(SubscriptionState.LIMITED.value)


class TestLimitedModeGuard:
    """Test limited mode guard function."""

    def test_guard_returns_true_when_operational(
        self,
        db: Session,
        org,
        subscription_active,
    ):
        """Test guard returns True when subscription operational."""
        guard = TillService.get_limited_mode_guard(org.id, db)
        assert guard() is True

    def test_guard_returns_false_when_limited(
        self,
        db: Session,
        org,
    ):
        """Test guard returns False when subscription LIMITED."""
        # Create LIMITED subscription
        yesterday = datetime.utcnow() - timedelta(days=2)
        from src.models.entities import Subscription
        sub = Subscription(
            organization_id=org.id,
            plan="BASIC",
            term=SubscriptionTerm.MONTHLY.value,
            state=SubscriptionState.LIMITED.value,
            start_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=datetime.utcnow() - timedelta(days=9),
            grace_end_date=yesterday,
        )
        db.add(sub)
        db.commit()

        guard = TillService.get_limited_mode_guard(org.id, db)
        assert guard() is False

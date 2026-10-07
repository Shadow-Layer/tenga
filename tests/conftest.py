"""Shared test fixtures."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.database import SessionLocal, init_db, drop_db
from src.models.entities import (
    Organization,
    User,
    Location,
    Product,
    Till,
    Subscription,
)
from src.models.subscription import SubscriptionState, SubscriptionTerm


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
def user(db: Session, org: Organization):
    """Create a test user (cashier)."""
    user = User(
        organization_id=org.id,
        email="cashier@test.com",
        username="cashier",
        full_name="Test Cashier",
        password_hash="hashed_password",
        role="operator",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def location(db: Session, org: Organization):
    """Create a test location."""
    location = Location(
        organization_id=org.id,
        code="LOC001",
        name="Main Store",
        is_active=True,
    )
    db.add(location)
    db.commit()
    return location


@pytest.fixture
def product(db: Session, org: Organization):
    """Create a test product."""
    product = Product(
        organization_id=org.id,
        sku="SKU001",
        name="Test Product",
        price=10.00,
        cost=5.00,
        is_active=True,
    )
    db.add(product)
    db.commit()
    return product


@pytest.fixture
def till(db: Session, org: Organization, location: Location):
    """Create a test till."""
    till = Till(
        organization_id=org.id,
        location_id=location.id,
        code="TILL001",
        name="Till 1",
        is_active=True,
    )
    db.add(till)
    db.commit()
    return till


@pytest.fixture
def subscription_active(db: Session, org: Organization):
    """Create an active subscription."""
    tomorrow = datetime.utcnow() + timedelta(days=30)
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

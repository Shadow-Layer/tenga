"""Shared test fixtures."""
import pytest
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# Set test database path before importing database modules
if "SQLITE_PATH" not in os.environ:
    os.environ["SQLITE_PATH"] = "./tenga-test.db"

from src.database import SessionLocal, init_db, drop_db, get_db
from src.models.entities import (
    Employee,
    EmployeeTillAssignment,
    Organization,
    User,
    Location,
    Product,
    Till,
    Subscription,
)
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.security.password import hash_password
from src.security.auth import create_access_token
from src.services.till_service import TillService
from src.main import app


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
    """Create a test user (cashier) with hashed password."""
    user = User(
        organization_id=org.id,
        email="cashier@test.com",
        username="cashier",
        full_name="Test Cashier",
        password_hash=hash_password("cashier_password"),
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
def open_pos_session(db: Session, org: Organization, till: Till):
    """Create an assigned cashier and their authenticated open till session."""
    def open_for(user: User):
        employee = Employee(
            organization_id=org.id,
            user_id=user.id,
            employee_number=f"POS-{user.id}",
            full_name=user.full_name,
            is_active=True,
        )
        db.add(employee)
        db.flush()
        db.add(EmployeeTillAssignment(employee_id=employee.id, till_id=till.id))
        db.commit()
        return TillService.open_session(
            organization_id=org.id,
            till_id=till.id,
            operator_id=user.id,
            opening_balance="0.00",
            db=db,
            enforce_assignment=True,
        )
    return open_for


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


@pytest.fixture
def client(db: Session, user: User):
    """Create a test client with dependency override and authentication."""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    
    # Login to get token
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "cashier@test.com", "password": "cashier_password"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        # Add authorization header to default headers
        test_client.headers["Authorization"] = f"Bearer {token}"
    
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(db: Session, admin_user: User):
    """Create an authenticated test client with catalog-management permissions."""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    
    # Login to get token
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin_password"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        # Add authorization header to default headers
        test_client.headers["Authorization"] = f"Bearer {token}"
    
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def subscription(db: Session, org: Organization):
    """Create a subscription (alias for subscription_active)."""
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



@pytest.fixture
def admin_user(db: Session, org: Organization):
    """Create a test admin user."""
    admin = User(
        organization_id=org.id,
        email="admin@test.com",
        username="admin",
        full_name="Test Admin",
        password_hash=hash_password("admin_password"),
        role="admin",
    )
    db.add(admin)
    db.commit()
    return admin


@pytest.fixture
def admin_client(db: Session, admin_user: User):
    """Create a test client authenticated as admin."""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    
    # Login to get token
    response = test_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin_password"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        test_client.headers["Authorization"] = f"Bearer {token}"
    
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db: Session):
    """Create a test client WITHOUT authentication."""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    
    # DO NOT add any auth header
    yield test_client
    app.dependency_overrides.clear()

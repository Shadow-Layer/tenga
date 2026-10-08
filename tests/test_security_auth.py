"""Security and authentication tests for T010."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database.config import SessionLocal, init_db, drop_db, get_db
from src.models.entities import Organization, User, Location, Product, Till
from src.models.subscription import SubscriptionState, SubscriptionTerm
from src.models.entities import Subscription
from src.main import app
from src.security.password import hash_password, verify_password
from src.security.auth import create_access_token, decode_access_token


# ==================== Fixtures ====================

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
def other_org(db: Session):
    """Create another test organization."""
    org = Organization(name="Other Org", code="OTHER")
    db.add(org)
    db.commit()
    return org


@pytest.fixture
def user(db: Session, org: Organization):
    """Create a test user (operator)."""
    user = User(
        organization_id=org.id,
        email="operator@test.com",
        username="operator",
        full_name="Test Operator",
        password_hash=hash_password("password123"),
        role="operator",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def manager_user(db: Session, org: Organization):
    """Create a test manager user."""
    user = User(
        organization_id=org.id,
        email="manager@test.com",
        username="manager",
        full_name="Test Manager",
        password_hash=hash_password("manager123"),
        role="manager",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def admin_user(db: Session, org: Organization):
    """Create a test admin user."""
    user = User(
        organization_id=org.id,
        email="admin@test.com",
        username="admin",
        full_name="Test Admin",
        password_hash=hash_password("admin123"),
        role="admin",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def other_org_user(db: Session, other_org: Organization):
    """Create a user in another organization."""
    user = User(
        organization_id=other_org.id,
        email="other@test.com",
        username="other",
        full_name="Other Org User",
        password_hash=hash_password("other123"),
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
def other_location(db: Session, other_org: Organization):
    """Create a location in another organization."""
    location = Location(
        organization_id=other_org.id,
        code="LOC002",
        name="Other Store",
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
def other_till(db: Session, other_org: Organization, other_location: Location):
    """Create a till in another organization."""
    till = Till(
        organization_id=other_org.id,
        location_id=other_location.id,
        code="TILL002",
        name="Till 2",
        is_active=True,
    )
    db.add(till)
    db.commit()
    return till


@pytest.fixture
def client(db: Session):
    """Create a test client with dependency override."""
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==================== Password Tests ====================

class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False
    
    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        hashed = hash_password("test")
        assert verify_password("", hashed) is False
        assert verify_password("test", "") is False


# ==================== JWT Token Tests ====================

class TestJWTTokens:
    """Test JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test creating an access token."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            organization_id=1,
            username="testuser",
            role="operator",
        )
        assert token is not None
        assert isinstance(token, str)
    
    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            organization_id=1,
            username="testuser",
            role="operator",
        )
        
        token_data = decode_access_token(token)
        assert token_data is not None
        assert token_data.user_id == 1
        assert token_data.email == "test@example.com"
        assert token_data.organization_id == 1
        assert token_data.username == "testuser"
        assert token_data.role == "operator"
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        token_data = decode_access_token("invalid_token")
        assert token_data is None
    
    def test_decode_expired_token(self):
        """Test decoding an expired token."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            organization_id=1,
            username="testuser",
            role="operator",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        token_data = decode_access_token(token)
        assert token_data is None


# ==================== Authentication Tests ====================

class TestAuthentication:
    """Test authentication endpoint."""
    
    def test_login_success(self, client: TestClient, user: User):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "operator@test.com"
    
    def test_login_invalid_email(self, client: TestClient, user: User):
        """Test login with invalid email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@test.com", "password": "password123"}
        )
        assert response.status_code == 401
    
    def test_login_invalid_password(self, client: TestClient, user: User):
        """Test login with incorrect password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client: TestClient, db: Session, org: Organization):
        """Test login with inactive user."""
        inactive_user = User(
            organization_id=org.id,
            email="inactive@test.com",
            username="inactive",
            password_hash=hash_password("password123"),
            role="operator",
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@test.com", "password": "password123"}
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, client: TestClient, user: User):
        """Test getting current user info."""
        # First login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Use token to get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "operator@test.com"
        assert data["username"] == "operator"


# ==================== Authorization Tests ====================

class TestAuthorizationOrganizationIsolation:
    """Test organization isolation."""
    
    def test_user_cannot_access_other_org_products(
        self, client: TestClient, user: User, other_org_user: User, 
        product: Product, db: Session
    ):
        """Test that user cannot access products from another organization."""
        # Create a product in another org
        other_product = Product(
            organization_id=other_org_user.organization_id,
            sku="OTHER_SKU",
            name="Other Product",
            price=20.00,
        )
        db.add(other_product)
        db.commit()
        
        # Login as first user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access product from other org (via direct ID manipulation)
        response = client.get(
            f"/api/v1/products/{other_product.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_user_cannot_list_other_org_products(
        self, client: TestClient, user: User, other_org: Organization
    ):
        """Test that user cannot list products from another organization."""
        # Login as first user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to list products from other org
        response = client.get(
            f"/api/v1/products?organization_id={other_org.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_user_cannot_access_other_org_locations(
        self, client: TestClient, user: User, other_location: Location
    ):
        """Test that user cannot access locations from another organization."""
        # Login as first user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access location from other org
        response = client.get(
            f"/api/v1/locations/{other_location.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_user_cannot_access_other_org_tills(
        self, client: TestClient, user: User, other_till: Till
    ):
        """Test that user cannot access tills from another organization."""
        # Login as first user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to access till from other org
        response = client.get(
            f"/api/v1/tills/{other_till.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403


class TestAuthorizationUnauthenticated:
    """Test unauthenticated access."""
    
    def test_unauthenticated_cannot_list_products(self, unauthenticated_client: TestClient):
        """Test that unauthenticated users cannot list products."""
        response = unauthenticated_client.get("/api/v1/products")
        assert response.status_code == 401  # Not authenticated
    
    def test_unauthenticated_cannot_list_locations(self, unauthenticated_client: TestClient):
        """Test that unauthenticated users cannot list locations."""
        response = unauthenticated_client.get("/api/v1/locations")
        assert response.status_code == 401
    
    def test_unauthenticated_cannot_list_tills(self, unauthenticated_client: TestClient):
        """Test that unauthenticated users cannot list tills."""
        response = unauthenticated_client.get("/api/v1/tills/")
        assert response.status_code == 401
    
    def test_unauthenticated_cannot_create_product(self, unauthenticated_client: TestClient, org: Organization):
        """Test that unauthenticated users cannot create products."""
        response = unauthenticated_client.post(
            "/api/v1/products",
            json={
                "organization_id": org.id,
                "sku": "TEST",
                "name": "Test",
                "price": 10.00,
            }
        )
        assert response.status_code == 401
    
    def test_unauthenticated_can_login(self, client: TestClient, user: User):
        """Test that unauthenticated users can login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        assert response.status_code == 200


class TestAuthorizationRoles:
    """Test role-based authorization."""
    
    def test_operator_cannot_create_user(
        self, client: TestClient, user: User, org: Organization
    ):
        """Test that operator cannot create users."""
        # Login as operator
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@test.com", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to create user
        response = client.post(
            f"/organizations/{org.id}/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "password123",
                "role": "operator",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    
    def test_manager_can_create_user(
        self, client: TestClient, manager_user: User, org: Organization
    ):
        """Test that manager can create users."""
        # Login as manager
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "manager@test.com", "password": "manager123"}
        )
        token = login_response.json()["access_token"]
        
        # Create user
        response = client.post(
            f"/organizations/{org.id}/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "password123",
                "role": "operator",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
    
    def test_admin_can_create_user(
        self, client: TestClient, admin_user: User, org: Organization
    ):
        """Test that admin can create users."""
        # Login as admin
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        
        # Create user
        response = client.post(
            f"/organizations/{org.id}/users",
            json={
                "username": "newuser",
                "email": "newuser@test.com",
                "password": "password123",
                "role": "operator",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201

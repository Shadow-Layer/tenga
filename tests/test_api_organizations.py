"""API tests for organizations and users endpoints."""
import pytest
from fastapi.testclient import TestClient

import src.config as app_config
from src.database import get_db
from src.models.entities import Organization, User
from src.main import app


@pytest.fixture
def fresh_setup_client(db, monkeypatch):
    """Provide an empty test database and the operator bootstrap secret."""
    monkeypatch.setattr(app_config, "INITIAL_SETUP_SECRET", "test-bootstrap-secret-" + "x" * 40)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


class TestOrganizations:
    """Tests for organization endpoints."""
    
    def test_anonymous_organization_creation_is_disabled(self, client: TestClient):
        """New organizations must be created with their first owner via bootstrap."""
        response = client.post(
            "/api/v1/organizations",
            json={"name": "Test Org New", "code": "NEW", "description": "Test"}
        )
        assert response.status_code == 410
    
    def test_get_organization(self, client: TestClient, org):
        """Test getting organization."""
        response = client.get(f"/api/v1/organizations/{org.id}")
        assert response.status_code == 200
        assert response.json()["id"] == org.id
    
    def test_get_nonexistent_organization(self, client: TestClient):
        """Test 404 for nonexistent organization."""
        response = client.get("/api/v1/organizations/99999")
        assert response.status_code == 404
    
    def test_list_organizations(self, client: TestClient, org):
        """Test listing organizations."""
        response = client.get("/api/v1/organizations")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
    
    def test_anonymous_organization_creation_stays_disabled(self, client: TestClient, org):
        """Existing organizations cannot use the anonymous creation route."""
        response = client.post(
            "/api/v1/organizations",
            json={"name": "Test Org", "code": "UNIQUE"}
        )
        assert response.status_code == 410


class TestInstallationBootstrap:
    """Tests for one-time organization and owner provisioning."""

    @staticmethod
    def payload():
        return {
            "organization": {
                "name": "Fresh Installation",
                "code": "FRESH",
                "description": "Local business",
            },
            "owner": {
                "username": "owner",
                "email": "owner@example.test",
                "full_name": "Store Owner",
                "password": "secure-owner-password",
            },
        }

    def test_bootstrap_requires_configured_secret(self, fresh_setup_client: TestClient):
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
        )
        assert response.status_code == 401

    def test_bootstrap_rejects_incorrect_secret(self, fresh_setup_client: TestClient):
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": "incorrect-secret"},
        )
        assert response.status_code == 401

    def test_bootstrap_rejects_password_over_bcrypt_limit(
        self, fresh_setup_client: TestClient, db
    ):
        payload = self.payload()
        payload["owner"]["password"] = "é" * 40
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=payload,
            headers={"X-Setup-Secret": app_config.INITIAL_SETUP_SECRET},
        )
        assert response.status_code == 422
        assert db.query(Organization).count() == 0

    def test_bootstrap_creates_owner_once(self, fresh_setup_client: TestClient, db):
        secret = app_config.INITIAL_SETUP_SECRET
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": secret},
        )
        assert response.status_code == 201
        result = response.json()
        assert result["organization"]["name"] == "Fresh Installation"
        assert result["owner"]["role"] == "admin"
        assert result["owner"]["organization_id"] == result["organization"]["id"]
        assert "password_hash" not in result["owner"]
        assert db.query(Organization).count() == 1
        assert db.query(User).count() == 1

        login = fresh_setup_client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.test", "password": "secure-owner-password"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "admin"

        with TestClient(app) as restarted_client:
            replay = restarted_client.post(
                "/api/v1/organizations/bootstrap",
                json=self.payload(),
                headers={"X-Setup-Secret": secret},
            )
        assert replay.status_code == 409
        assert db.query(Organization).count() == 1
        assert db.query(User).count() == 1

    def test_owner_creation_failure_rolls_back_organization(
        self, fresh_setup_client: TestClient, db
    ):
        from sqlalchemy import text

        db.execute(text(
            "CREATE TRIGGER reject_bootstrap_owner BEFORE INSERT ON user "
            "BEGIN SELECT RAISE(ABORT, 'injected user insert failure'); END"
        ))
        db.commit()
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": app_config.INITIAL_SETUP_SECRET},
        )
        assert response.status_code == 409
        assert db.query(Organization).count() == 0
        assert db.query(User).count() == 0

    def test_organization_creation_failure_leaves_database_empty(
        self, fresh_setup_client: TestClient, db
    ):
        from sqlalchemy import text

        db.execute(text(
            "CREATE TRIGGER reject_bootstrap_organization BEFORE INSERT ON organization "
            "BEGIN SELECT RAISE(ABORT, 'injected organization insert failure'); END"
        ))
        db.commit()
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": app_config.INITIAL_SETUP_SECRET},
        )
        assert response.status_code == 409
        assert db.query(Organization).count() == 0
        assert db.query(User).count() == 0

    def test_bootstrap_rejects_existing_data_without_changes(
        self, fresh_setup_client: TestClient, db, org
    ):
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": app_config.INITIAL_SETUP_SECRET},
        )
        assert response.status_code == 409
        assert db.query(Organization).count() == 1
        assert db.query(User).count() == 0

    def test_bootstrap_rejects_missing_deployment_secret(
        self, fresh_setup_client: TestClient, monkeypatch
    ):
        monkeypatch.setattr(app_config, "INITIAL_SETUP_SECRET", "")
        response = fresh_setup_client.post(
            "/api/v1/organizations/bootstrap",
            json=self.payload(),
            headers={"X-Setup-Secret": "provided-but-not-configured"},
        )
        assert response.status_code == 503


class TestUsers:
    """Tests for user endpoints."""
    
    def test_create_user(self, admin_client: TestClient, org):
        """Test creating user."""
        response = admin_client.post(
            f"/api/v1/organizations/{org.id}/users",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "newuser_secure_password",
                "role": "operator"
            }
        )
        assert response.status_code == 201
        assert response.json()["email"] == "newuser@test.com"
    
    def test_get_user(self, client: TestClient, org, user):
        """Test getting user."""
        response = client.get(f"/api/v1/organizations/{org.id}/users/{user.id}")
        assert response.status_code == 200
        assert response.json()["id"] == user.id
    
    def test_list_users(self, client: TestClient, org, user):
        """Test listing users."""
        response = client.get(f"/api/v1/organizations/{org.id}/users")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
    
    def test_duplicate_email(self, admin_client: TestClient, org, user):
        """Test 409 for duplicate email."""
        response = admin_client.post(
            f"/api/v1/organizations/{org.id}/users",
            json={
                "email": "cashier@test.com",
                "username": "different",
                "full_name": "Other",
                "password": "secure_password",
                "role": "operator"
            }
        )
        assert response.status_code == 409

"""API tests for organizations and users endpoints."""
import pytest
from fastapi.testclient import TestClient


class TestOrganizations:
    """Tests for organization endpoints."""
    
    def test_create_organization(self, client: TestClient):
        """Test creating organization."""
        response = client.post(
            "/organizations",
            json={"name": "Test Org New", "code": "NEW", "description": "Test"}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test Org New"
    
    def test_get_organization(self, client: TestClient, org):
        """Test getting organization."""
        response = client.get(f"/organizations/{org.id}")
        assert response.status_code == 200
        assert response.json()["id"] == org.id
    
    def test_get_nonexistent_organization(self, client: TestClient):
        """Test 404 for nonexistent organization."""
        response = client.get("/organizations/99999")
        assert response.status_code == 404
    
    def test_list_organizations(self, client: TestClient, org):
        """Test listing organizations."""
        response = client.get("/organizations")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
    
    def test_duplicate_organization_name(self, client: TestClient, org):
        """Test 409 for duplicate name."""
        response = client.post(
            "/organizations",
            json={"name": "Test Org", "code": "UNIQUE"}
        )
        assert response.status_code == 409


class TestUsers:
    """Tests for user endpoints."""
    
    def test_create_user(self, admin_client: TestClient, org):
        """Test creating user."""
        response = admin_client.post(
            f"/organizations/{org.id}/users",
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
        response = client.get(f"/organizations/{org.id}/users/{user.id}")
        assert response.status_code == 200
        assert response.json()["id"] == user.id
    
    def test_list_users(self, client: TestClient, org, user):
        """Test listing users."""
        response = client.get(f"/organizations/{org.id}/users")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
    
    def test_duplicate_email(self, admin_client: TestClient, org, user):
        """Test 409 for duplicate email."""
        response = admin_client.post(
            f"/organizations/{org.id}/users",
            json={
                "email": "cashier@test.com",
                "username": "different",
                "full_name": "Other",
                "password": "secure_password",
                "role": "operator"
            }
        )
        assert response.status_code == 409

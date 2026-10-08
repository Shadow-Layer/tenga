"""API tests for tills."""
import pytest
from fastapi.testclient import TestClient


class TestTills:
    """Tests for till endpoints."""
    
    def test_create_till(self, client: TestClient, org, location):
        """Test creating till."""
        response = client.post(
            "/api/v1/tills",
            json={
                "organization_id": org.id,
                "location_id": location.id,
                "code": "TILL999",
                "name": "New Till"
            }
        )
        assert response.status_code == 201
        assert response.json()["code"] == "TILL999"
    
    def test_get_till(self, client: TestClient, till):
        """Test getting till."""
        response = client.get(f"/api/v1/tills/{till.id}")
        assert response.status_code == 200
        assert response.json()["id"] == till.id
    
    def test_list_tills(self, client: TestClient, org, till):
        """Test listing tills."""
        response = client.get(f"/api/v1/tills?organization_id={org.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
    
    def test_get_till_status(self, client: TestClient, till):
        """Test getting till status."""
        response = client.get(f"/api/v1/tills/{till.id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_open" in data
    
    def test_open_till(self, client: TestClient, till, user, subscription):
        """Test opening till."""
        response = client.post(
            f"/api/v1/tills/{till.id}/open",
            json={"user_id": user.id}
        )
        assert response.status_code == 201
        assert response.json()["is_open"] is True
    
    def test_close_till(self, client: TestClient, till, user, subscription):
        """Test closing till."""
        # Open first
        client.post(
            f"/api/v1/tills/{till.id}/open",
            json={"user_id": user.id}
        )
        
        # Then close
        response = client.post(
            f"/api/v1/tills/{till.id}/close",
            json={"user_id": user.id, "closing_amount_cents": 5000.0}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CLOSED"
    
    def test_open_already_open_till(self, client: TestClient, till, user, subscription):
        """Test 409 when opening already open till."""
        client.post(
            f"/api/v1/tills/{till.id}/open",
            json={"user_id": user.id}
        )
        
        response = client.post(
            f"/api/v1/tills/{till.id}/open",
            json={"user_id": user.id}
        )
        assert response.status_code == 409
    
    def test_nonexistent_till(self, client: TestClient):
        """Test 404 for nonexistent till."""
        response = client.get("/api/v1/tills/99999")
        assert response.status_code == 404

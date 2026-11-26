"""API tests for subscriptions."""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient


class TestSubscriptions:
    """Tests for subscription endpoints."""
    
    def test_create_subscription(self, admin_client: TestClient, org):
        """Test creating subscription."""
        response = admin_client.post(
            f"/api/v1/subscriptions/{org.id}",
            json={
                "plan_type": "MONTHLY",
                "start_date": datetime.utcnow().isoformat()
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["organization_id"] == org.id
        assert data["state"] == "ACTIVE"
    
    def test_get_subscription(self, client: TestClient, org, subscription):
        """Test getting subscription."""
        response = client.get(f"/api/v1/subscriptions/{org.id}")
        assert response.status_code == 200
        assert response.json()["organization_id"] == org.id
    
    def test_get_subscription_state(self, client: TestClient, org, subscription):
        """Test getting subscription state."""
        response = client.get(f"/api/v1/subscriptions/{org.id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "operational" in data
    
    def test_renew_subscription(self, admin_client: TestClient, org, subscription):
        """Test renewing subscription."""
        response = admin_client.post(
            f"/api/v1/subscriptions/{org.id}/renew",
            json={}
        )
        assert response.status_code == 200
        assert response.json()["state"] == "ACTIVE"
    
    def test_duplicate_subscription(self, admin_client: TestClient, org, subscription):
        """Test 409 for duplicate subscription."""
        response = admin_client.post(
            f"/api/v1/subscriptions/{org.id}",
            json={
                "plan_type": "MONTHLY",
                "start_date": datetime.utcnow().isoformat()
            }
        )
        assert response.status_code == 409
    
    def test_nonexistent_org(self, client: TestClient):
        """Test 404 for nonexistent organization."""
        response = client.get("/api/v1/subscriptions/99999")
        assert response.status_code == 403

"""API tests for tills."""
import pytest
from fastapi.testclient import TestClient

from src.models.entities import Employee, EmployeeTillAssignment, Till


@pytest.fixture
def assigned_till(db, org, till, user):
    employee = Employee(
        organization_id=org.id,
        employee_number="EMP-TILL-001",
        full_name="Test Cashier",
        user_id=user.id,
    )
    db.add(employee)
    db.flush()
    db.add(EmployeeTillAssignment(employee_id=employee.id, till_id=till.id))
    db.commit()
    return till


class TestTills:
    """Tests for till endpoints."""
    
    def test_create_till(self, admin_client: TestClient, org, location):
        """Test creating till."""
        response = admin_client.post(
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
    
    def test_get_till(self, client: TestClient, assigned_till):
        """Test getting till."""
        response = client.get(f"/api/v1/tills/{assigned_till.id}")
        assert response.status_code == 200
        assert response.json()["id"] == assigned_till.id
    
    def test_list_tills(self, client: TestClient, org, assigned_till):
        """Test listing tills."""
        response = client.get(f"/api/v1/tills?organization_id={org.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0

    def test_list_assigned_tills_only_returns_active_operator_assignments(
        self, client: TestClient, db, org, location, assigned_till
    ):
        unassigned = Till(
            organization_id=org.id,
            location_id=location.id,
            code="UNASSIGNED",
            name="Unassigned till",
            is_active=True,
        )
        db.add(unassigned)
        db.commit()

        response = client.get("/api/v1/tills/assigned")

        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [assigned_till.id]

    def test_list_assigned_tills_returns_empty_without_employee_assignment(
        self, client: TestClient, till
    ):
        response = client.get("/api/v1/tills/assigned")

        assert response.status_code == 200
        assert response.json()["items"] == []
    
    def test_get_till_status(self, client: TestClient, assigned_till):
        """Test getting till status."""
        response = client.get(f"/api/v1/tills/{assigned_till.id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "is_open" in data
    
    def test_open_till(self, client: TestClient, assigned_till, user, subscription):
        """Test opening till."""
        response = client.post(
            f"/api/v1/tills/{assigned_till.id}/open",
            json={"user_id": user.id}
        )
        assert response.status_code == 201
        assert response.json()["is_open"] is True
    
    def test_close_till(self, client: TestClient, assigned_till, user, subscription):
        """Test closing till."""
        # Open first
        opened = client.post(
            f"/api/v1/tills/{assigned_till.id}/open",
            json={"user_id": user.id}
        )
        
        # Then close
        response = client.post(
            f"/api/v1/tills/{assigned_till.id}/close",
            json={
                "user_id": user.id,
                "session_id": opened.json()["session_id"],
                "closing_balance": 50.0,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "CLOSED"
    
    def test_open_already_open_till(self, client: TestClient, assigned_till, user, subscription):
        """Test 409 when opening already open till."""
        client.post(
            f"/api/v1/tills/{assigned_till.id}/open",
            json={"user_id": user.id}
        )
        
        response = client.post(
            f"/api/v1/tills/{assigned_till.id}/open",
            json={"user_id": user.id}
        )
        assert response.status_code == 409
    
    def test_nonexistent_till(self, client: TestClient):
        """Test 404 for nonexistent till."""
        response = client.get("/api/v1/tills/99999")
        assert response.status_code == 404

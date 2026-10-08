"""API tests for sales."""
import pytest
from fastapi.testclient import TestClient


class TestSales:
    """Tests for sales endpoints."""
    
    def test_create_sale(self, client: TestClient, till, product, user):
        """Test creating sale."""
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "cashier_id": user.id,
                "payment_method": "CASH",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        assert response.status_code == 201
    
    def test_get_sale(self, client: TestClient, till, product, user):
        """Test getting sale."""
        # Create sale first
        create_resp = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "cashier_id": user.id,
                "payment_method": "CASH",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        sale_id = create_resp.json()["id"]
        
        # Get sale
        response = client.get(f"/api/v1/sales/{sale_id}")
        assert response.status_code == 200
    
    def test_list_sales(self, client: TestClient, till, product, user):
        """Test listing sales."""
        # Create sale first
        client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "cashier_id": user.id,
                "payment_method": "CASH",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        
        response = client.get(f"/api/v1/sales?till_id={till.id}")
        assert response.status_code == 200
    
    def test_commit_sale(self, client: TestClient, till, product, user):
        """Test committing sale."""
        # Create sale
        create_resp = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "cashier_id": user.id,
                "payment_method": "CASH",
                "items": [
                    {"product_id": product.id, "quantity": 5, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        sale_id = create_resp.json()["id"]
        
        # Commit sale
        response = client.post(
            f"/api/v1/sales/{sale_id}/commit",
            json={"user_id": user.id}
        )
        assert response.status_code == 200
    
    def test_oversell_allowed(self, client: TestClient, till, product, user):
        """Test that overselling is allowed."""
        response = client.post(
            "/api/v1/sales",
            json={
                "till_id": till.id,
                "cashier_id": user.id,
                "payment_method": "CASH",
                "items": [
                    {"product_id": product.id, "quantity": 1000, "unit_price": 10.00}
                ],
                "is_offline": False
            }
        )
        # Should succeed despite overselling
        assert response.status_code == 201

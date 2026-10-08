"""API tests for products and locations."""
import pytest
from fastapi.testclient import TestClient


class TestProducts:
    """Tests for product endpoints."""
    
    def test_create_product(self, client: TestClient, org):
        """Test creating product."""
        response = client.post(
            "/api/v1/products",
            json={
                "organization_id": org.id,
                "sku": "NEWSKU",
                "name": "New Product",
                "price": 20.00,
                "cost": 10.00
            }
        )
        assert response.status_code == 201
        assert response.json()["sku"] == "NEWSKU"
    
    def test_get_product(self, client: TestClient, product):
        """Test getting product."""
        response = client.get(f"/api/v1/products/{product.id}")
        assert response.status_code == 200
        assert response.json()["id"] == product.id
    
    def test_list_products(self, client: TestClient, org, product):
        """Test listing products."""
        response = client.get(f"/api/v1/products?organization_id={org.id}")
        assert response.status_code == 200
        assert response.json()["total"] > 0
    
    def test_duplicate_sku(self, client: TestClient, org, product):
        """Test 409 for duplicate SKU."""
        response = client.post(
            "/api/v1/products",
            json={
                "organization_id": org.id,
                "sku": "SKU001",  # Same as product fixture
                "name": "Another",
                "price": 15.00,
                "cost": 7.00
            }
        )
        assert response.status_code == 409
    
    def test_nonexistent_org(self, client: TestClient):
        """Test 403 for cross-organization access (proper auth behavior)."""
        response = client.post(
            "/api/v1/products",
            json={
                "organization_id": 99999,
                "sku": "SKU",
                "name": "Product",
                "price": 10.00,
                "cost": 5.00
            }
        )
        assert response.status_code == 403


class TestLocations:
    """Tests for location endpoints."""
    
    def test_create_location(self, client: TestClient, org):
        """Test creating location."""
        response = client.post(
            "/api/v1/locations",
            json={
                "organization_id": org.id,
                "code": "LOC999",
                "name": "New Store"
            }
        )
        assert response.status_code == 201
        assert response.json()["code"] == "LOC999"
    
    def test_get_location(self, client: TestClient, location):
        """Test getting location."""
        response = client.get(f"/api/v1/locations/{location.id}")
        assert response.status_code == 200
        assert response.json()["id"] == location.id
    
    def test_list_locations(self, client: TestClient, org, location):
        """Test listing locations."""
        response = client.get(f"/api/v1/locations?organization_id={org.id}")
        assert response.status_code == 200
        assert response.json()["total"] > 0


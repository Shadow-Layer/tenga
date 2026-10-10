"""API tests for inventory."""
import pytest
from fastapi.testclient import TestClient
from src.models.entities import Stock


class TestInventory:
    """Tests for inventory endpoints - basic validation."""
    
    def test_inventory_endpoints_available(self, authenticated_client: TestClient):
        """Test that inventory endpoints are available and respond."""
        # Test movements endpoint with auth
        response = authenticated_client.get("/api/v1/stock/stock/movements")
        assert response.status_code in [200, 400, 422]  # Not 500


class TestStockAdjustmentReasonValidation:
    """Tests for stock adjustment endpoint reason validation."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db, org, user, location, product):
        """Setup stock for each test."""
        stock = Stock(
            organization_id=org.id,
            product_id=product.id,
            location_id=location.id,
            quantity=100,
        )
        db.add(stock)
        db.commit()
    
    def test_adjust_with_canonical_code_physical_count_discrepancy(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with canonical code PHYSICAL_COUNT_DISCREPANCY."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -5,
                "reason": "PHYSICAL_COUNT_DISCREPANCY",
                "note": "Test adjustment with canonical code"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "PHYSICAL_COUNT_DISCREPANCY"
    
    def test_adjust_with_canonical_code_damage(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with canonical code DAMAGE."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -3,
                "reason": "DAMAGE",
                "note": "Product damaged"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "DAMAGE"
    
    def test_adjust_with_canonical_code_shrinkage(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with canonical code SHRINKAGE."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -2,
                "reason": "SHRINKAGE",
                "note": "Shrinkage adjustment"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "SHRINKAGE"
    
    def test_adjust_with_canonical_code_adjustment(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with canonical code ADJUSTMENT."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": 5,
                "reason": "ADJUSTMENT",
                "note": "Generic adjustment"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "ADJUSTMENT"
    
    def test_adjust_with_label_physical_count_discrepancy(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with label 'Physical Count Discrepancy' converts to canonical."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -1,
                "reason": "Physical Count Discrepancy",
                "note": "Count discrepancy"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "PHYSICAL_COUNT_DISCREPANCY", "Label should be converted to canonical code"
    
    def test_adjust_with_label_damage(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with label 'Damage' converts to canonical."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -2,
                "reason": "Damage",
                "note": "Damaged product"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "DAMAGE", "Label should be converted to canonical code"
    
    def test_adjust_with_label_shrinkage(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with label 'Shrinkage' converts to canonical."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -1,
                "reason": "Shrinkage",
                "note": "Shrinkage"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "SHRINKAGE", "Label should be converted to canonical code"
    
    def test_adjust_with_label_adjustment(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with label 'Adjustment' converts to canonical."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": 3,
                "reason": "Adjustment",
                "note": "Adjustment"
            }
        )
        assert response.status_code == 201, f"Response: {response.json()}"
        data = response.json()
        assert data["reason"] == "ADJUSTMENT", "Label should be converted to canonical code"
    
    def test_adjust_with_invalid_reason_returns_400(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with invalid reason returns 400 Bad Request."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -1,
                "reason": "INVALID_REASON",
                "note": "Invalid reason"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "Invalid adjustment reason" in data["detail"]
    
    def test_adjust_with_unknown_label_returns_400(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with unknown label returns 400 Bad Request."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -1,
                "reason": "Unknown Reason",
                "note": "Unknown label"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "Invalid adjustment reason" in data["detail"]
    
    def test_adjust_with_empty_reason_returns_400(
        self, authenticated_client: TestClient, product, location
    ):
        """Test adjustment with empty reason returns 400 Bad Request."""
        response = authenticated_client.post(
            "/api/v1/stock/stock/adjust",
            json={
                "product_id": product.id,
                "location_id": location.id,
                "quantity": -1,
                "reason": "",
                "note": "Empty reason"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "Invalid adjustment reason" in data["detail"]

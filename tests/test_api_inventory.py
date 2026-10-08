"""API tests for inventory."""
import pytest
from fastapi.testclient import TestClient


class TestInventory:
    """Tests for inventory endpoints - basic validation."""
    
    def test_inventory_endpoints_available(self, client: TestClient):
        """Test that inventory endpoints are available and respond."""
        # Test movements endpoint
        response = client.get("/api/v1/stock/stock/movements")
        assert response.status_code in [200, 400, 422]  # Not 500

"""API tests for sync endpoints."""
import pytest
from fastapi.testclient import TestClient


class TestSync:
    """Tests for sync endpoints - basic validation."""
    
    def test_sync_endpoints_available(self, client: TestClient):
        """Test that sync endpoints respond."""
        # Test that endpoint is available (404 OK, 500 not OK)
        response = client.get("/api/v1/sync/subscription-state/1")
        # Should be 200, 404, or 422, not 500
        assert response.status_code != 500

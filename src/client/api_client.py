"""HTTP client for communicating with Tenga Inventory API.

Handles authentication, request formatting, and response parsing.
"""

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """HTTP client for Tenga Inventory API."""

    def __init__(self, base_url: str, auth_token: str = None):
        """Initialize API client.
        
        Args:
            base_url: Base URL for API (e.g., http://localhost:8000)
            auth_token: JWT token for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()
        
        # Configure retries (using allowed_methods for newer urllib3)
        try:
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
                backoff_factor=1
            )
        except TypeError:
            # Fallback for older urllib3 versions
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
                backoff_factor=1
            )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def set_auth_token(self, token: str) -> None:
        """Set authentication token."""
        self.auth_token = token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _make_request(self, method: str, endpoint: str, data: Dict = None,
                     params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative path)
            data: Request body data
            params: Query parameters
        
        Returns:
            Response JSON
        
        Raises:
            APIError: On HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}")

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and get authentication token.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            Response with token and user info
        """
        return self._make_request(
            "POST",
            "/api/v1/auth/login",
            data={"email": email, "password": password}
        )

    def get_organization(self, org_id: int) -> Dict[str, Any]:
        """Get organization details.
        
        Args:
            org_id: Organization ID
        
        Returns:
            Organization data
        """
        return self._make_request("GET", f"/api/v1/organizations/{org_id}")

    def get_locations(self, org_id: int) -> List[Dict[str, Any]]:
        """Get locations for organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            List of locations
        """
        response = self._make_request("GET", f"/api/v1/organizations/{org_id}/locations")
        return response.get("locations", []) if isinstance(response, dict) else response

    def get_products(self, org_id: int) -> List[Dict[str, Any]]:
        """Get product catalog for organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            List of products
        """
        response = self._make_request("GET", f"/api/v1/organizations/{org_id}/products")
        return response.get("products", []) if isinstance(response, dict) else response

    def get_stock(self, org_id: int, location_id: int) -> List[Dict[str, Any]]:
        """Get stock for location.
        
        Args:
            org_id: Organization ID
            location_id: Location ID
        
        Returns:
            List of stock items
        """
        response = self._make_request(
            "GET",
            f"/api/v1/organizations/{org_id}/locations/{location_id}/stock"
        )
        return response.get("stock", []) if isinstance(response, dict) else response

    def get_subscription_state(self, org_id: int) -> Dict[str, Any]:
        """Get subscription state for organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            Subscription state
        """
        return self._make_request("GET", f"/api/v1/subscriptions/{org_id}/state/sync")

    def submit_sync_batch(self, device_id: str, org_id: int, 
                         items: List[Dict]) -> Dict[str, Any]:
        """Submit batch of offline transactions for sync.
        
        Args:
            device_id: Device ID
            org_id: Organization ID
            items: Batch items to sync
        
        Returns:
            Sync response with acknowledgments
        """
        return self._make_request(
            "POST",
            "/api/v1/sync/batch",
            data={
                "device_id": device_id,
                "organization_id": org_id,
                "items": items
            }
        )

    def get_sync_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a sync batch.
        
        Args:
            batch_id: Batch ID
        
        Returns:
            Batch status
        """
        return self._make_request("GET", f"/api/v1/sync/status/{batch_id}")

    def cache_subscription_state(self, device_id: str, org_id: int,
                                subscription_state: Dict) -> Dict[str, Any]:
        """Cache subscription state on device.
        
        Args:
            device_id: Device ID
            org_id: Organization ID
            subscription_state: Subscription state to cache
        
        Returns:
            Cache update response
        """
        return self._make_request(
            "POST",
            "/api/v1/cache/subscription-state",
            data={
                "device_id": device_id,
                "organization_id": org_id,
                "subscription_state": subscription_state
            }
        )

    def close(self) -> None:
        """Close HTTP session."""
        if self.session:
            self.session.close()


class APIError(Exception):
    """API error."""
    pass

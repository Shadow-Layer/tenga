"""Mock ZIMRA service for testing fiscal integration."""
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MockZimraMode(Enum):
    """Simulation mode for mock ZIMRA service."""
    SUCCESS = "success"  # Normal success
    OFFLINE = "offline"  # Simulates timeout/connection error
    ERROR_VALIDATION = "error_validation"  # 400 validation error
    ERROR_AUTH = "error_auth"  # 401 authentication error
    ERROR_DEVICE = "error_device"  # 403 device error
    ERROR_SERVER = "error_server"  # 500 server error
    ERROR_TRANSIENT = "error_transient"  # 503 transient error
    ERROR_UNCERTAIN = "error_uncertain"  # Uncertain error (response lost)


class MockZimraService:
    """Mock ZIMRA service for testing without real API calls."""
    
    def __init__(self, mode: MockZimraMode = MockZimraMode.SUCCESS):
        """
        Initialize mock ZIMRA service.
        
        Args:
            mode: Simulation mode (determines behavior)
        """
        self.mode = mode
        self.submissions = {}  # Store submissions by fiscal_number
        self.fiscal_counter = 1000
        self.call_count = 0
    
    def submit_fiscal_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock fiscal submission.
        
        Args:
            payload: Fiscal request payload
            
        Returns:
            Mock ZIMRA response
            
        Raises:
            Exception: Depends on mode
        """
        self.call_count += 1
        
        if self.mode == MockZimraMode.OFFLINE:
            raise TimeoutError("Mock ZIMRA offline (timeout)")
        
        elif self.mode == MockZimraMode.ERROR_VALIDATION:
            raise ValueError("Mock ZIMRA: Validation error (400)")
        
        elif self.mode == MockZimraMode.ERROR_AUTH:
            raise PermissionError("Mock ZIMRA: Authentication failed (401)")
        
        elif self.mode == MockZimraMode.ERROR_DEVICE:
            raise PermissionError("Mock ZIMRA: Device not approved (403)")
        
        elif self.mode == MockZimraMode.ERROR_SERVER:
            raise RuntimeError("Mock ZIMRA: Server error (500)")
        
        elif self.mode == MockZimraMode.ERROR_TRANSIENT:
            raise RuntimeError("Mock ZIMRA: Service unavailable (503)")
        
        elif self.mode == MockZimraMode.ERROR_UNCERTAIN:
            raise ConnectionError("Mock ZIMRA: Uncertain error (response lost)")
        
        # SUCCESS mode
        fiscal_number = f"ZWE-{self.fiscal_counter:08d}"
        self.fiscal_counter += 1
        
        # Store submission
        self.submissions[fiscal_number] = {
            "payload": payload,
            "status": "acknowledged",
            "timestamp": payload.get("timestamp")
        }
        
        logger.info(f"Mock ZIMRA: Submission successful, fiscal number: {fiscal_number}")
        
        return {
            "fiscal_number": fiscal_number,
            "status": "acknowledged",
            "message": "Fiscal submission accepted",
            "timestamp": payload.get("timestamp")
        }
    
    def query_fiscal_status(self, receipt_id: str) -> Dict[str, Any]:
        """
        Mock fiscal status query.
        
        Args:
            receipt_id: Fiscal receipt ID
            
        Returns:
            Mock status response
        """
        if self.mode == MockZimraMode.OFFLINE:
            raise TimeoutError("Mock ZIMRA offline")
        
        if receipt_id in self.submissions:
            return {
                "fiscal_number": receipt_id,
                "status": self.submissions[receipt_id]["status"],
                "timestamp": self.submissions[receipt_id]["timestamp"]
            }
        
        return {
            "fiscal_number": receipt_id,
            "status": "unknown",
            "message": "Fiscal number not found"
        }
    
    def check_device_status(self) -> Dict[str, Any]:
        """
        Mock device status check.
        
        Returns:
            Mock device status
        """
        if self.mode == MockZimraMode.OFFLINE:
            raise TimeoutError("Mock ZIMRA offline")
        
        return {
            "device_id": "DEV-MOCK-001",
            "status": "online",
            "last_heartbeat": None
        }
    
    def set_mode(self, mode: MockZimraMode) -> None:
        """Change mock service mode."""
        self.mode = mode
        logger.info(f"Mock ZIMRA mode changed to: {mode.value}")
    
    def reset(self) -> None:
        """Reset mock service state."""
        self.submissions = {}
        self.fiscal_counter = 1000
        self.call_count = 0

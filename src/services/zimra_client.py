"""ZIMRA Fiscal Device Gateway API client for fiscal submission and status monitoring."""
import os
import time
import logging
from typing import Optional, Dict, Any
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of ZIMRA API errors."""
    TRANSIENT = "transient"  # Retry-able (timeout, 500, 429)
    PERMANENT = "permanent"  # Don't retry (400, 401, 403)
    UNCERTAIN = "uncertain"  # Response lost (safe to retry with idempotency)


class SubmissionError(Exception):
    """Error submitting request to ZIMRA."""
    def __init__(self, message: str, error_type: ErrorType, response_code: Optional[int] = None):
        self.message = message
        self.error_type = error_type
        self.response_code = response_code
        super().__init__(message)


class ZimraClient:
    """HTTP client for ZIMRA Fiscal Device Gateway API."""
    
    def __init__(self):
        """Initialize ZIMRA client with configuration from environment."""
        self.api_url = os.getenv("ZIMRA_API_URL", "https://fdms.zimra.co.zw").rstrip("/")
        self.device_id = os.getenv("ZIMRA_DEVICE_ID", "").strip()
        self.api_key = os.getenv("ZIMRA_API_KEY", "").strip()
        self.timeout = int(os.getenv("ZIMRA_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("ZIMRA_MAX_RETRIES", "5"))
        
        # Validate configuration
        if not self.api_url:
            raise ValueError("ZIMRA_API_URL not configured")
        if not self.device_id:
            raise ValueError("ZIMRA_DEVICE_ID not configured")
        if not self.api_key:
            raise ValueError("ZIMRA_API_KEY not configured")
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=1  # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Device-ID": self.device_id,
            "User-Agent": "TengaVFD/1.0"
        }
    
    def _classify_error(self, status_code: int) -> ErrorType:
        """Classify HTTP error as transient, permanent, or uncertain."""
        if status_code in (400, 401, 403):
            return ErrorType.PERMANENT
        elif status_code in (408, 429, 500, 502, 503, 504):
            return ErrorType.TRANSIENT
        else:
            return ErrorType.UNCERTAIN
    
    def submit_fiscal_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit fiscal request to ZIMRA.
        
        Args:
            payload: Validated fiscal request data
            
        Returns:
            Response from ZIMRA with fiscal_number and status
            
        Raises:
            SubmissionError: If submission fails (with error classification)
        """
        try:
            response = self.session.post(
                f"{self.api_url}/fiscal/submit",
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # Success
            if response.status_code == 200:
                logger.info(f"Fiscal submission successful for sale {payload.get('sale_id')}")
                return response.json()
            
            # Error
            error_type = self._classify_error(response.status_code)
            error_msg = f"ZIMRA API error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, error_type, response.status_code)
            
        except requests.Timeout as e:
            error_msg = f"ZIMRA request timeout after {self.timeout}s"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.TRANSIENT)
        
        except requests.ConnectionError as e:
            error_msg = f"ZIMRA connection error: {str(e)[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.TRANSIENT)
        
        except requests.RequestException as e:
            error_msg = f"ZIMRA request error: {str(e)[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.UNCERTAIN)
    
    def query_fiscal_status(self, receipt_id: str) -> Dict[str, Any]:
        """
        Query status of a fiscal submission.
        
        Args:
            receipt_id: ZIMRA-assigned fiscal receipt ID
            
        Returns:
            Status response from ZIMRA
            
        Raises:
            SubmissionError: If query fails
        """
        try:
            response = self.session.get(
                f"{self.api_url}/fiscal/query/{receipt_id}",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Fiscal status query successful for receipt {receipt_id}")
                return response.json()
            
            error_type = self._classify_error(response.status_code)
            error_msg = f"ZIMRA query error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, error_type, response.status_code)
            
        except requests.Timeout:
            error_msg = "ZIMRA query timeout"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.TRANSIENT)
        
        except requests.RequestException as e:
            error_msg = f"ZIMRA query error: {str(e)[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.UNCERTAIN)
    
    def check_device_status(self) -> Dict[str, Any]:
        """
        Check ZIMRA device connectivity and status.
        
        Returns:
            Device status from ZIMRA
            
        Raises:
            SubmissionError: If status check fails
        """
        try:
            response = self.session.get(
                f"{self.api_url}/fiscal/device/status",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info("ZIMRA device status check successful")
                return response.json()
            
            error_type = self._classify_error(response.status_code)
            error_msg = f"ZIMRA device status error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, error_type, response.status_code)
            
        except requests.Timeout:
            error_msg = "ZIMRA device status check timeout"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.TRANSIENT)
        
        except requests.RequestException as e:
            error_msg = f"ZIMRA device status error: {str(e)[:200]}"
            logger.error(error_msg)
            raise SubmissionError(error_msg, ErrorType.UNCERTAIN)
    
    def close(self):
        """Close session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

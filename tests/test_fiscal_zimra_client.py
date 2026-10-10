"""Tests for ZIMRA Fiscal Device Gateway API client (T1)."""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from src.services.zimra_client import ZimraClient, SubmissionError, ErrorType
from datetime import datetime


class TestZimraClientConfiguration:
    """Test ZIMRA client configuration from environment."""
    
    def test_client_initialization_with_env_vars(self):
        """Test client initializes correctly with environment variables."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'test-api-key',
            'ZIMRA_TIMEOUT': '30',
            'ZIMRA_MAX_RETRIES': '5'
        }):
            client = ZimraClient()
            assert client.api_url == 'https://test.zimra.co.zw'
            assert client.device_id == 'DEV-12345'
            assert client.timeout == 30
            assert client.max_retries == 5
            client.close()
    
    def test_client_requires_api_url(self):
        """Test client raises error if API URL not configured."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': '',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }, clear=False):
            with pytest.raises(ValueError, match="ZIMRA_API_URL"):
                ZimraClient()
    
    def test_client_requires_device_id(self):
        """Test client raises error if device ID not configured."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': '',
            'ZIMRA_API_KEY': 'key'
        }, clear=False):
            with pytest.raises(ValueError, match="ZIMRA_DEVICE_ID"):
                ZimraClient()
    
    def test_client_requires_api_key(self):
        """Test client raises error if API key not configured."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': ''
        }, clear=False):
            with pytest.raises(ValueError, match="ZIMRA_API_KEY"):
                ZimraClient()
    
    def test_client_strips_url_trailing_slash(self):
        """Test client strips trailing slash from API URL."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw/',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            assert client.api_url == 'https://test.zimra.co.zw'
            client.close()


class TestZimraErrorClassification:
    """Test error classification logic."""
    
    def test_permanent_error_400(self):
        """Test 400 Bad Request is classified as permanent."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(400)
            assert error_type == ErrorType.PERMANENT
            client.close()
    
    def test_permanent_error_401(self):
        """Test 401 Unauthorized is classified as permanent."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(401)
            assert error_type == ErrorType.PERMANENT
            client.close()
    
    def test_permanent_error_403(self):
        """Test 403 Forbidden is classified as permanent."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(403)
            assert error_type == ErrorType.PERMANENT
            client.close()
    
    def test_transient_error_429(self):
        """Test 429 Too Many Requests is classified as transient."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(429)
            assert error_type == ErrorType.TRANSIENT
            client.close()
    
    def test_transient_error_500(self):
        """Test 500 Server Error is classified as transient."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(500)
            assert error_type == ErrorType.TRANSIENT
            client.close()
    
    def test_transient_error_503(self):
        """Test 503 Service Unavailable is classified as transient."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            error_type = client._classify_error(503)
            assert error_type == ErrorType.TRANSIENT
            client.close()


class TestZimraSubmissionRequest:
    """Test fiscal submission request."""
    
    @patch('src.services.zimra_client.requests.Session.post')
    def test_submit_fiscal_request_success(self, mock_post):
        """Test successful fiscal submission."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'fiscal_number': 'ZWE-12345678',
            'status': 'acknowledged'
        }
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            payload = {
                'sale_id': 'SALE-001',
                'device_id': 'DEV-12345',
                'timestamp': datetime.utcnow().isoformat(),
                'items': [],
                'subtotal': '100.00',
                'tax_amount': '15.00',
                'total': '115.00',
                'payment_method': 'CASH',
                'idempotency_key': 'KEY-001'
            }
            
            result = client.submit_fiscal_request(payload)
            
            assert result['fiscal_number'] == 'ZWE-12345678'
            assert result['status'] == 'acknowledged'
            client.close()
    
    @patch('src.services.zimra_client.requests.Session.post')
    def test_submit_fiscal_request_permanent_error(self, mock_post):
        """Test permanent error (400) is not retried."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid request'
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            payload = {'sale_id': 'SALE-001', 'device_id': 'DEV-12345'}
            
            with pytest.raises(SubmissionError) as exc_info:
                client.submit_fiscal_request(payload)
            
            assert exc_info.value.error_type == ErrorType.PERMANENT
            client.close()
    
    @patch('src.services.zimra_client.requests.Session.post')
    def test_submit_fiscal_request_timeout(self, mock_post):
        """Test timeout error is classified as transient."""
        import requests
        mock_post.side_effect = requests.Timeout("Connection timeout")
        
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            payload = {'sale_id': 'SALE-001'}
            
            with pytest.raises(SubmissionError) as exc_info:
                client.submit_fiscal_request(payload)
            
            assert exc_info.value.error_type == ErrorType.TRANSIENT
            client.close()


class TestZimraAuthHeaders:
    """Test authentication header generation."""
    
    def test_auth_headers_include_bearer_token(self):
        """Test headers include Bearer token."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'test-secret-key'
        }):
            client = ZimraClient()
            headers = client._get_headers()
            
            assert 'Authorization' in headers
            assert headers['Authorization'] == 'Bearer test-secret-key'
            client.close()
    
    def test_auth_headers_include_device_id(self):
        """Test headers include device ID."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-UNIQUE',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            headers = client._get_headers()
            
            assert 'X-Device-ID' in headers
            assert headers['X-Device-ID'] == 'DEV-UNIQUE'
            client.close()
    
    def test_auth_headers_include_content_type(self):
        """Test headers include Content-Type."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            client = ZimraClient()
            headers = client._get_headers()
            
            assert headers['Content-Type'] == 'application/json'
            client.close()


class TestZimraContextManager:
    """Test context manager usage."""
    
    def test_context_manager_closes_session(self):
        """Test context manager properly closes session."""
        with patch.dict(os.environ, {
            'ZIMRA_API_URL': 'https://test.zimra.co.zw',
            'ZIMRA_DEVICE_ID': 'DEV-12345',
            'ZIMRA_API_KEY': 'key'
        }):
            with ZimraClient() as client:
                assert client.session is not None

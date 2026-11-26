"""Server-side Paynow transport boundary.

The configured endpoint is an adapter-compatible API URL. Provider credentials are
read only at request time and are never included in the persisted request payload.
"""
import hashlib
import hmac
import os
from typing import Any, Dict
from urllib.parse import quote, urlparse

import requests


class PaynowConfigurationError(RuntimeError):
    pass


class PaynowTransportError(RuntimeError):
    def __init__(self, message: str, *, uncertain: bool):
        self.uncertain = uncertain
        super().__init__(message)


class PaynowAdapter:
    """Small adapter for the server-to-server Paynow integration contract."""

    def __init__(self, *, session=None):
        self.base_url = os.getenv("PAYNOW_API_URL", "").strip().rstrip("/")
        self.integration_id = os.getenv("PAYNOW_INTEGRATION_ID", "").strip()
        self.integration_key = os.getenv("PAYNOW_INTEGRATION_KEY", "").strip()
        self.callback_secret = os.getenv("PAYNOW_CALLBACK_SECRET", "").strip()
        self.callback_url = os.getenv("PAYNOW_CALLBACK_URL", "").strip()
        self.return_url = os.getenv("PAYNOW_RETURN_URL", "").strip()
        self.timeout = float(os.getenv("PAYNOW_TIMEOUT_SECONDS", "15"))
        self.session = session or requests.Session()
        if not all((
            self.base_url,
            self.integration_id,
            self.integration_key,
            self.callback_secret,
            self.callback_url,
            self.return_url,
        )):
            raise PaynowConfigurationError(
                "Paynow server-side configuration is incomplete"
            )
        endpoint = urlparse(self.base_url)
        local_host = endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        if not endpoint.netloc or (endpoint.scheme != "https" and not local_host):
            raise PaynowConfigurationError("Paynow API URL must use HTTPS")
        for configured_url in (self.callback_url, self.return_url):
            parsed_url = urlparse(configured_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                raise PaynowConfigurationError(
                    "Paynow callback and return URLs must use HTTPS"
                )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.integration_key}",
            "X-Paynow-Integration-Id": self.integration_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def initiate(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(request_data)
        payload["callback_url"] = self.callback_url
        payload["return_url"] = self.return_url
        try:
            response = self.session.post(
                f"{self.base_url}/v1/payments",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PaynowTransportError(
                "Paynow initiation outcome is unknown", uncertain=True
            ) from exc
        if response.status_code >= 500 or response.status_code in (408, 429):
            raise PaynowTransportError(
                "Paynow initiation outcome is unknown", uncertain=True
            )
        if response.status_code >= 400:
            raise PaynowTransportError(
                "Paynow rejected the initiation request", uncertain=False
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise PaynowTransportError(
                "Paynow returned an invalid initiation response", uncertain=True
            ) from exc
        if not isinstance(body, dict):
            raise PaynowTransportError(
                "Paynow returned an invalid initiation response", uncertain=True
            )
        return body

    def verify(self, merchant_reference: str) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}/v1/payments/{quote(merchant_reference, safe='')}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PaynowTransportError(
                "Paynow status is temporarily unavailable", uncertain=True
            ) from exc
        if response.status_code >= 400:
            raise PaynowTransportError(
                "Paynow status is temporarily unavailable", uncertain=True
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise PaynowTransportError(
                "Paynow returned an invalid status response", uncertain=True
            ) from exc
        if not isinstance(body, dict):
            raise PaynowTransportError(
                "Paynow returned an invalid status response", uncertain=True
            )
        return body

    def verify_callback_signature(self, raw_body: bytes, signature: str) -> bool:
        expected = hmac.new(
            self.callback_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, (signature or "").strip().lower())

    def close(self) -> None:
        self.session.close()


def create_paynow_adapter() -> PaynowAdapter:
    return PaynowAdapter()

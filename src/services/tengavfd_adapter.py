"""Transport boundary for the server-side TengaVFD HTTP contract."""

import os
from typing import Any, Dict
from urllib.parse import quote, urlparse

import requests


class FiscalConfigurationError(RuntimeError):
    pass


class FiscalTransportError(RuntimeError):
    def __init__(self, message: str, *, uncertain: bool):
        self.uncertain = uncertain
        super().__init__(message)


class TengaVFDAdapter:
    """HTTP adapter that returns provider results without manufacturing success."""

    def __init__(self, *, session=None):
        self.base_url = os.getenv("TENGAVFD_API_URL", "").strip().rstrip("/")
        self.api_token = os.getenv("TENGAVFD_API_TOKEN", "").strip()
        self.device_id = os.getenv("TENGAVFD_DEVICE_ID", "").strip()
        self.timeout = float(os.getenv("TENGAVFD_TIMEOUT_SECONDS", "20"))
        self.session = session or requests.Session()
        if not self.base_url or not self.api_token or not self.device_id:
            raise FiscalConfigurationError(
                "TengaVFD server-side configuration is incomplete"
            )
        endpoint = urlparse(self.base_url)
        local_host = endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        if not endpoint.netloc or (endpoint.scheme != "https" and not local_host):
            raise FiscalConfigurationError("TengaVFD API URL must use HTTPS")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "X-TengaVFD-Device-ID": self.device_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def submit(self, request_reference: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.session.post(
                f"{self.base_url}/v1/submissions",
                json={"request_reference": request_reference, "receipt": payload},
                headers={
                    **self._headers(),
                    "Idempotency-Key": request_reference,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FiscalTransportError(
                "Fiscal submission outcome is unknown", uncertain=True
            ) from exc
        if response.status_code >= 500 or response.status_code in (408, 429):
            raise FiscalTransportError(
                "Fiscal submission outcome is unknown", uncertain=True
            )
        if response.status_code >= 400:
            raise FiscalTransportError(
                "Fiscal provider rejected the submission", uncertain=False
            )
        return self._json_response(response)

    def status(self, request_reference: str) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}/v1/submissions/{quote(request_reference, safe='')}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise FiscalTransportError(
                "Fiscal status is temporarily unavailable", uncertain=True
            ) from exc
        if response.status_code >= 400:
            raise FiscalTransportError(
                "Fiscal status is temporarily unavailable", uncertain=True
            )
        return self._json_response(response)

    @staticmethod
    def _json_response(response) -> Dict[str, Any]:
        try:
            result = response.json()
        except ValueError as exc:
            raise FiscalTransportError(
                "Fiscal provider returned an invalid response", uncertain=True
            ) from exc
        if not isinstance(result, dict):
            raise FiscalTransportError(
                "Fiscal provider returned an invalid response", uncertain=True
            )
        return result

    def close(self) -> None:
        self.session.close()


def create_tengavfd_adapter() -> TengaVFDAdapter:
    return TengaVFDAdapter()

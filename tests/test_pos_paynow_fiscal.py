"""Focused tests for server-verified Paynow settlement and independent fiscal state."""

import json
import hashlib
import hmac
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError

from src.models.entities import (
    FiscalSubmission,
    InventoryMovement,
    Location,
    Organization,
    Payment,
    PaymentAttempt,
    ReceiptAudit,
    Sale,
    Till,
    User,
)
from src.services.paynow_adapter import PaynowTransportError
from src.services.paynow_adapter import PaynowAdapter
from src.services.tengavfd_adapter import TengaVFDAdapter


class MockPaynowAdapter:
    def __init__(self):
        self.initiations = 0
        self.verifications = 0
        self.request = None
        self.timeout_on_initiate = False
        self.remote_result = {}
        self.provider_reference = None

    def initiate(self, request_data):
        self.initiations += 1
        self.request = dict(request_data)
        if self.timeout_on_initiate:
            raise PaynowTransportError("simulated timeout", uncertain=True)
        self.provider_reference = f"provider-ref-{self.initiations}"
        return {
            "merchant_reference": request_data["merchant_reference"],
            "provider_reference": self.provider_reference,
            "redirect_url": "https://paynow.example/redirect/1",
        }

    def verify(self, merchant_reference):
        self.verifications += 1
        return {
            "merchant_reference": merchant_reference,
            "provider_reference": self.provider_reference or "provider-ref-1",
            **self.remote_result,
        }

    @staticmethod
    def verify_callback_signature(raw_body, signature):
        return signature == "valid-test-signature"

    @staticmethod
    def close():
        return None


class MockFiscalAdapter:
    def __init__(self):
        self.submissions = 0
        self.request_reference = None
        self.payload = None
        self.remote_result = {"status": "UNCERTAIN"}

    def submit(self, request_reference, payload):
        self.submissions += 1
        self.request_reference = request_reference
        self.payload = payload
        return {"request_reference": request_reference, **self.remote_result}

    def status(self, request_reference):
        assert request_reference == self.request_reference
        return {"request_reference": request_reference, **self.remote_result}

    @staticmethod
    def close():
        return None


class MockHttpResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class MockHttpSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def close(self):
        self.closed = True


def paynow_payload(till, session, product, *, key="paynow-op-0001", method="HOSTED"):
    return {
        "till_id": till.id,
        "till_session_id": session.id,
        "idempotency_key": key,
        "payment_method": "PAYNOW",
        "paynow_method": method,
        "phone_number": "+263771234567" if method == "MOBILE_MONEY" else None,
        "items": [
            {
                "product_id": product.id,
                "quantity": 1,
                "unit_price": str(product.price),
                "tax_rate": "0",
                "tax_inclusive": False,
            }
        ],
    }


def test_provider_adapters_use_mock_transport_and_server_credentials(
    monkeypatch,
):
    monkeypatch.setenv("PAYNOW_API_URL", "https://paynow.test")
    monkeypatch.setenv("PAYNOW_INTEGRATION_ID", "merchant-id")
    monkeypatch.setenv("PAYNOW_INTEGRATION_KEY", "provider-secret")
    monkeypatch.setenv("PAYNOW_CALLBACK_SECRET", "callback-secret")
    monkeypatch.setenv("PAYNOW_CALLBACK_URL", "https://pos.test/api/v1/paynow/callback")
    monkeypatch.setenv("PAYNOW_RETURN_URL", "https://pos.test/checkout/return")
    paynow_transport = MockHttpSession(
        MockHttpResponse({
            "merchant_reference": "merchant-ref",
            "provider_reference": "provider-ref",
            "redirect_url": "https://paynow.test/redirect",
        }),
        MockHttpResponse({
            "merchant_reference": "merchant-ref",
            "provider_reference": "provider-ref",
            "status": "PENDING",
            "amount": "10.00",
            "currency": "USD",
        }),
    )
    paynow = PaynowAdapter(session=paynow_transport)
    initiated = paynow.initiate({
        "merchant_reference": "merchant-ref",
        "amount": "10.00",
        "currency": "USD",
        "payment_method": "HOSTED",
    })
    verified = paynow.verify("merchant-ref")
    assert initiated["redirect_url"] == "https://paynow.test/redirect"
    assert verified["status"] == "PENDING"
    assert paynow_transport.calls[0][2]["headers"]["Authorization"] == "Bearer provider-secret"
    assert "integration_key" not in paynow_transport.calls[0][2]["json"]
    raw_body = b'{"status":"PENDING"}'
    signature = hmac.new(
        b"callback-secret", raw_body, hashlib.sha256
    ).hexdigest()
    assert paynow.verify_callback_signature(raw_body, signature)

    monkeypatch.setenv("TENGAVFD_API_URL", "https://vfd.test")
    monkeypatch.setenv("TENGAVFD_API_TOKEN", "fiscal-secret")
    monkeypatch.setenv("TENGAVFD_DEVICE_ID", "device-1")
    fiscal_transport = MockHttpSession(
        MockHttpResponse({
            "request_reference": "fiscal-ref",
            "status": "SUBMITTED",
        }),
        MockHttpResponse({
            "request_reference": "fiscal-ref",
            "status": "ACKNOWLEDGED",
            "fiscal_number": "VFD-987",
        }),
    )
    fiscal = TengaVFDAdapter(session=fiscal_transport)
    submitted = fiscal.submit("fiscal-ref", {"sale_id": "1"})
    reconciled = fiscal.status("fiscal-ref")
    assert submitted["status"] == "SUBMITTED"
    assert reconciled["fiscal_number"] == "VFD-987"
    assert fiscal_transport.calls[0][2]["headers"]["Idempotency-Key"] == "fiscal-ref"
    assert "api_token" not in fiscal_transport.calls[0][2]["json"]
    paynow.close()
    fiscal.close()
    assert paynow_transport.closed and fiscal_transport.closed


def test_paynow_pending_duplicate_initiation_and_timeout_recovery(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    payload = paynow_payload(till, session, product, method="MOBILE_MONEY")

    first = client.post("/api/v1/sales", json=payload)
    assert first.status_code == 201
    attempt = db.query(PaymentAttempt).one()
    sale = db.query(Sale).one()
    assert first.json()["status"] == "PENDING"
    assert first.json()["redirect_url"] == "https://paynow.example/redirect/1"
    assert adapter.request["amount"] == "10.00"
    assert adapter.request["currency"] == "USD"
    assert adapter.request["phone_number"] == "+263771234567"
    assert sale.status == "PENDING"
    assert sale.till_session_id == session.id
    assert attempt.amount == Decimal("10.00")
    assert not hasattr(attempt, "phone_number")
    assert db.query(Payment).count() == 0
    assert db.query(InventoryMovement).count() == 0
    assert db.query(ReceiptAudit).count() == 0

    replay = client.post("/api/v1/sales", json=payload)
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    assert adapter.initiations == 1


def test_paynow_timeout_is_not_reinitiated_and_unverified_result_has_no_stock(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    adapter.timeout_on_initiate = True
    adapter.remote_result = {
        "status": "PENDING",
        "amount": "10.00",
        "currency": "USD",
    }
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    payload = paynow_payload(till, session, product)

    first = client.post("/api/v1/sales", json=payload)
    replay = client.post("/api/v1/sales", json=payload)
    assert first.status_code == replay.status_code == 201
    assert first.json()["status"] == "UNCERTAIN"
    assert adapter.initiations == 1

    status = client.get(f"/api/v1/sales/{first.json()['sale_id']}/paynow")
    assert status.status_code == 200
    assert status.json()["status"] == "PENDING"
    assert adapter.verifications == 1
    assert db.query(Payment).count() == 0
    assert db.query(InventoryMovement).count() == 0


def test_offline_sale_commit_cannot_settle_unverified_paynow(
    client: TestClient,
    db,
    org,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    created = client.post(
        "/api/v1/sales",
        json=paynow_payload(till, session, product),
    )
    sale_id = created.json()["sale_id"]

    sync = client.post(
        "/api/v1/sync/batch",
        json={
            "organization_id": org.id,
            "device_id": "pos-device",
            "operations": [{
                "operation_id": "do-not-settle-paynow",
                "operation_type": "SALE_COMMIT",
                "payload": {"sale_id": sale_id},
            }],
        },
    )
    assert sync.status_code == 200
    assert sync.json()["acknowledgements"][0]["status"] == "TERMINAL_FAILURE"
    db.refresh(db.query(Sale).one())
    assert db.query(Sale).one().status == "PENDING"
    assert db.query(Payment).count() == 0
    assert db.query(InventoryMovement).count() == 0


def test_paynow_retries_only_after_terminal_failure(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    adapter.remote_result = {
        "status": "FAILED",
        "amount": "10.00",
        "currency": "USD",
    }
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    created = client.post(
        "/api/v1/sales",
        json=paynow_payload(till, session, product),
    )
    failed = client.get(f"/api/v1/sales/{created.json()['sale_id']}/paynow")
    assert failed.json()["status"] == "FAILED"

    retry = client.post(f"/api/v1/paynow/{failed.json()['id']}/retry", json={})
    assert retry.status_code == 201
    assert retry.json()["status"] == "PENDING"
    assert retry.json()["merchant_reference"] != failed.json()["merchant_reference"]
    assert adapter.initiations == 2
    assert db.query(PaymentAttempt).count() == 2
    root = db.query(PaymentAttempt).filter_by(id=failed.json()["id"]).one()
    child = db.query(PaymentAttempt).filter_by(id=retry.json()["id"]).one()
    assert child.retry_of_attempt_id == root.id

    replay = client.post(f"/api/v1/paynow/{root.id}/retry", json={})
    assert replay.status_code == 201
    assert replay.json()["id"] == child.id
    assert adapter.initiations == 2
    assert db.query(PaymentAttempt).count() == 2

    duplicate_child = PaymentAttempt(
        organization_id=root.organization_id,
        sale_id=root.sale_id,
        retry_of_attempt_id=root.id,
        till_session_id=root.till_session_id,
        initiated_by_id=root.initiated_by_id,
        provider=root.provider,
        payment_method=root.payment_method,
        merchant_reference="duplicate-retry-child",
        amount=root.amount,
        currency_code=root.currency_code,
        status="PENDING",
    )
    db.add(duplicate_child)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    adapter.remote_result = {
        "status": "FAILED",
        "amount": "10.00",
        "currency": "USD",
    }
    failed_child = client.get(
        f"/api/v1/sales/{created.json()['sale_id']}/paynow"
    )
    assert failed_child.json()["id"] == child.id
    assert failed_child.json()["status"] == "FAILED"
    next_retry = client.post(
        f"/api/v1/paynow/{child.id}/retry",
        json={},
    )
    assert next_retry.status_code == 201
    newest = db.query(PaymentAttempt).filter_by(id=next_retry.json()["id"]).one()
    assert newest.retry_of_attempt_id == child.id
    assert adapter.initiations == 3

    old_replay = client.post(f"/api/v1/paynow/{root.id}/retry", json={})
    assert old_replay.status_code == 201
    assert old_replay.json()["id"] == child.id
    assert adapter.initiations == 3
    assert db.query(PaymentAttempt).count() == 3
    assert db.query(Payment).count() == 0
    assert db.query(InventoryMovement).count() == 0


def test_paynow_retry_uncertain_replay_never_reinitiates(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    adapter.remote_result = {
        "status": "FAILED",
        "amount": "10.00",
        "currency": "USD",
    }
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    created = client.post(
        "/api/v1/sales",
        json=paynow_payload(till, session, product),
    )
    failed = client.get(f"/api/v1/sales/{created.json()['sale_id']}/paynow")
    assert failed.json()["status"] == "FAILED"

    adapter.timeout_on_initiate = True
    retry = client.post(
        f"/api/v1/paynow/{failed.json()['id']}/retry",
        json={},
    )
    assert retry.status_code == 201
    assert retry.json()["status"] == "UNCERTAIN"
    assert adapter.initiations == 2

    replay = client.post(
        f"/api/v1/paynow/{failed.json()['id']}/retry",
        json={},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == retry.json()["id"]
    assert replay.json()["status"] == "UNCERTAIN"
    assert adapter.initiations == 2
    assert db.query(PaymentAttempt).count() == 2
    assert db.query(Payment).count() == 0
    assert db.query(InventoryMovement).count() == 0


def test_paynow_callback_hash_remote_verification_and_duplicate_settlement(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    adapter = MockPaynowAdapter()
    adapter.remote_result = {
        "status": "PENDING",
        "amount": "10.00",
        "currency": "USD",
    }
    monkeypatch.setattr(
        "src.services.paynow_service.create_paynow_adapter",
        lambda: adapter,
    )
    created = client.post(
        "/api/v1/sales",
        json=paynow_payload(till, session, product),
    )
    attempt = db.query(PaymentAttempt).one()
    callback = {
        "merchant_reference": attempt.merchant_reference,
        "provider_reference": "provider-ref-1",
        "status": "PAID",
        "amount": "10.00",
        "currency": "USD",
    }
    invalid = client.post(
        "/api/v1/paynow/callback",
        content=json.dumps(callback),
        headers={"X-Paynow-Signature": "invalid"},
    )
    assert invalid.status_code == 401
    assert adapter.verifications == 0

    valid_but_not_remote_paid = client.post(
        "/api/v1/paynow/callback",
        content=json.dumps(callback),
        headers={"X-Paynow-Signature": "valid-test-signature"},
    )
    assert valid_but_not_remote_paid.status_code == 200
    assert valid_but_not_remote_paid.json()["status"] == "PENDING"
    assert db.query(InventoryMovement).count() == 0
    assert db.query(Payment).count() == 0

    adapter.remote_result = {
        "status": "PAID",
        "amount": "9.99",
        "currency": "USD",
    }
    mismatch = client.get(f"/api/v1/sales/{created.json()['sale_id']}/paynow")
    assert mismatch.status_code == 200
    assert mismatch.json()["status"] == "FAILED"
    assert db.query(InventoryMovement).count() == 0

    adapter.remote_result = {
        "status": "PAID",
        "amount": "10.00",
        "currency": "USD",
    }
    settled = client.post(
        "/api/v1/paynow/callback",
        content=json.dumps({**callback, "status": "FAILED"}),
        headers={"X-Paynow-Signature": "valid-test-signature"},
    )
    duplicate = client.post(
        "/api/v1/paynow/callback",
        content=json.dumps(callback),
        headers={"X-Paynow-Signature": "valid-test-signature"},
    )
    assert settled.status_code == duplicate.status_code == 200
    assert settled.json()["status"] == "SETTLED"
    assert duplicate.json()["status"] == "SETTLED"
    assert db.query(Payment).count() == 1
    assert db.query(InventoryMovement).count() == 1
    assert db.query(ReceiptAudit).count() == 1
    assert db.query(Sale).one().status == "COMPLETED"


def test_fiscal_status_is_independent_and_never_invents_acknowledgement(
    client: TestClient,
    db,
    till,
    user,
    product,
    open_pos_session,
    monkeypatch,
):
    session = open_pos_session(user)
    cash_sale = client.post(
        "/api/v1/sales",
        json={
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "fiscal-independent-001",
            "payment_method": "CASH",
            "amount_tendered": "10.00",
            "items": [{"product_id": product.id, "quantity": 1}],
        },
    )
    assert cash_sale.status_code == 201
    sale_id = cash_sale.json()["id"]
    adapter = MockFiscalAdapter()
    monkeypatch.setattr(
        "src.services.fiscal_service.create_tengavfd_adapter",
        lambda: adapter,
    )

    first = client.post(f"/api/v1/sales/{sale_id}/fiscal/submit", json={})
    assert first.status_code == 200
    assert first.json()["status"] == "UNCERTAIN"
    submission = db.query(FiscalSubmission).one()
    saved_payload = submission.request_payload
    assert submission.fiscal_number is None
    db.refresh(db.query(Sale).one())
    sale = db.query(Sale).one()
    assert sale.status == "COMPLETED"
    assert sale.fiscal_number is None
    assert sale.fiscal_status == "UNCERTAIN"

    replay = client.post(f"/api/v1/sales/{sale_id}/fiscal/submit", json={})
    assert replay.json()["id"] == first.json()["id"]
    assert adapter.submissions == 1
    assert submission.request_payload == saved_payload

    adapter.remote_result = {
        "status": "ACKNOWLEDGED",
        "fiscal_number": "VFD-REAL-123",
    }
    reconciled = client.post(f"/api/v1/sales/{sale_id}/fiscal/reconcile")
    assert reconciled.status_code == 200
    assert reconciled.json()["status"] == "ACKNOWLEDGED"
    assert reconciled.json()["fiscal_number"] == "VFD-REAL-123"
    db.refresh(sale)
    assert sale.status == "COMPLETED"
    assert sale.fiscal_number == "VFD-REAL-123"
    assert sale.fiscal_status == "ACKNOWLEDGED"
    assert db.query(InventoryMovement).count() == 1


def test_fiscal_routes_are_tenant_scoped(
    admin_client: TestClient,
    db,
    org,
):
    other_org = Organization(name="Fiscal Other", code="FISCAL-OTHER")
    db.add(other_org)
    db.flush()
    other_user = User(
        organization_id=other_org.id,
        email="fiscal-other@example.test",
        username="fiscal-other",
        full_name="Other",
        password_hash="unused",
        role="operator",
    )
    db.add(other_user)
    db.flush()
    other_location = Location(
        organization_id=other_org.id,
        code="FISCAL-LOC",
        name="Other location",
        is_active=True,
    )
    db.add(other_location)
    db.flush()
    other_till = Till(
        organization_id=other_org.id,
        location_id=other_location.id,
        code="OTHER-TILL",
        name="Other Till",
    )
    db.add(other_till)
    db.flush()
    foreign_sale = Sale(
        organization_id=other_org.id,
        till_id=other_till.id,
        cashier_id=other_user.id,
        total_amount=Decimal("1.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        amount_tendered=Decimal("1.00"),
        change_given=Decimal("0.00"),
        payment_method="CASH",
        status="COMPLETED",
        currency_code="USD",
    )
    db.add(foreign_sale)
    db.commit()

    response = admin_client.get(f"/api/v1/sales/{foreign_sale.id}/fiscal/status")
    assert response.status_code == 404

import pytest
from fastapi.testclient import TestClient

import src.config as app_config
from src.database import get_db
from src.models.entities import Organization, Sale
from src.main import app


@pytest.fixture
def fresh_setup_client(db, monkeypatch):
    monkeypatch.setattr(app_config, "INITIAL_SETUP_SECRET", "test-bootstrap-secret-" + "x" * 40)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def test_admin_can_update_organization_settings_before_activity(
    admin_client: TestClient, org: Organization, db
):
    response = admin_client.patch(
        f"/api/v1/organizations/{org.id}",
        json={
            "name": "Corner Shop",
            "phone": "+263 77 000 0000",
            "address": "1 Main Street",
            "region": "Harare",
            "timezone": "Africa/Harare",
            "currency_code": "zwl",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Corner Shop"
    assert response.json()["currency_code"] == "ZWL"
    assert response.json()["timezone"] == "Africa/Harare"
    db.refresh(org)
    assert org.currency_code == "ZWL"


def test_non_admin_cannot_update_organization(client: TestClient, org: Organization):
    response = client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"phone": "555-0100"},
    )

    assert response.status_code == 403


def test_currency_change_is_locked_after_sale(
    admin_client: TestClient,
    org: Organization,
    admin_user,
    till,
    db,
):
    sale = Sale(
        organization_id=org.id,
        till_id=till.id,
        cashier_id=admin_user.id,
        total_amount=10,
        payment_method="cash",
        currency_code="USD",
    )
    db.add(sale)
    db.commit()

    response = admin_client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"currency_code": "ZWL"},
    )

    assert response.status_code == 409
    db.refresh(org)
    assert org.currency_code == "USD"


def test_legacy_currency_confirmation_does_not_rewrite_sale(
    admin_client: TestClient,
    org: Organization,
    admin_user,
    till,
    db,
):
    org.currency_code = None
    sale = Sale(
        organization_id=org.id,
        till_id=till.id,
        cashier_id=admin_user.id,
        total_amount=10,
        payment_method="cash",
        currency_code=None,
    )
    db.add(sale)
    db.commit()

    rejected = admin_client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"currency_code": "USD"},
    )
    assert rejected.status_code == 409

    confirmed = admin_client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"currency_code": "USD", "confirm_legacy_currency": True},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["currency_code"] == "USD"
    db.refresh(sale)
    assert sale.currency_code is None


def test_currency_code_must_be_three_letters(admin_client: TestClient, org: Organization):
    response = admin_client.patch(
        f"/api/v1/organizations/{org.id}",
        json={"currency_code": "US"},
    )

    assert response.status_code == 422


def test_cross_tenant_organization_update_returns_not_found(admin_client: TestClient, db):
    other_org = Organization(name="Other Org", code="OTHER")
    db.add(other_org)
    db.commit()

    response = admin_client.patch(
        f"/api/v1/organizations/{other_org.id}",
        json={"phone": "555-0100"},
    )

    assert response.status_code == 404


def test_bootstrap_persists_organization_settings(fresh_setup_client: TestClient):
    payload = {
        "organization": {
            "name": "Fresh Organization",
            "code": "FRESHORG",
            "description": "Small business",
            "phone": "+263 77 000 0000",
            "region": "Harare",
            "timezone": "Africa/Harare",
            "currency_code": "zwl",
        },
        "owner": {
            "username": "owner",
            "email": "owner@example.test",
            "full_name": "Store Owner",
            "password": "secure-owner-password",
        },
    }
    response = fresh_setup_client.post(
        "/api/v1/organizations/bootstrap",
        json=payload,
        headers={"X-Setup-Secret": app_config.INITIAL_SETUP_SECRET},
    )

    assert response.status_code == 201
    organization = response.json()["organization"]
    assert organization["currency_code"] == "ZWL"
    assert organization["phone"] == "+263 77 000 0000"
    assert organization["timezone"] == "Africa/Harare"

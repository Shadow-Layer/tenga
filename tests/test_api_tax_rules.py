"""Tax-rule authorization, isolation, and price calculation tests."""
from fastapi.testclient import TestClient

from src.models.entities import TaxRule


def test_tax_rule_management_requires_manager(
    client: TestClient, org
):
    response = client.post(
        "/api/v1/tax-rules",
        json={"name": "VAT", "rate": "15.00", "tax_inclusive": False},
    )
    assert response.status_code == 403


def test_tax_rules_are_organization_scoped(
    admin_client: TestClient, db, org
):
    rule = TaxRule(
        organization_id=org.id,
        name="VAT",
        rate="15.00",
        tax_inclusive=False,
        is_active=True,
    )
    db.add(rule)
    db.commit()

    response = admin_client.get("/api/v1/tax-rules")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [rule.id]


def test_tax_inclusive_and_exclusive_sales_are_rounded_per_line(
    admin_client: TestClient, db, org, product, till, admin_user, open_pos_session
):
    session = open_pos_session(admin_user)
    inclusive = TaxRule(
        organization_id=org.id,
        name="Inclusive",
        rate="2.50",
        tax_inclusive=True,
        is_active=True,
    )
    exclusive = TaxRule(
        organization_id=org.id,
        name="Exclusive",
        rate="12.50",
        tax_inclusive=False,
        is_active=True,
    )
    db.add_all([inclusive, exclusive])
    db.flush()
    product.price = "0.22"
    product.tax_rule_id = inclusive.id
    db.commit()

    inclusive_response = admin_client.post(
        "/api/v1/sales",
        json={
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "tax-inclusive-0001",
            "payment_method": "CASH",
            "expected_total": "0.22",
            "amount_tendered": "0.22",
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "0.22",
                    "tax_rate": "2.50",
                    "tax_inclusive": True,
                }
            ],
        },
    )
    assert inclusive_response.status_code == 201
    inclusive_sale = inclusive_response.json()
    assert inclusive_sale["total_amount"] == 0.22
    assert inclusive_sale["tax_amount"] == 0.01
    assert inclusive_sale["sale_items"][0]["unit_price"] == 0.22
    assert inclusive_sale["sale_items"][0]["tax_inclusive"] is True

    product.price = "0.20"
    product.tax_rule_id = exclusive.id
    db.commit()
    exclusive_response = admin_client.post(
        "/api/v1/sales",
        json={
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "tax-exclusive-0001",
            "payment_method": "CASH",
            "expected_total": "0.23",
            "amount_tendered": "0.23",
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                    "unit_price": "0.20",
                    "tax_rate": "12.50",
                    "tax_inclusive": False,
                }
            ],
        },
    )
    assert exclusive_response.status_code == 201
    exclusive_sale = exclusive_response.json()
    assert exclusive_sale["total_amount"] == 0.23
    assert exclusive_sale["tax_amount"] == 0.03
    assert exclusive_sale["sale_items"][0]["tax_inclusive"] is False


def test_product_can_explicitly_omit_tax(
    admin_client: TestClient, db, product, till, admin_user, open_pos_session
):
    session = open_pos_session(admin_user)
    product.price = "0.20"
    product.tax_rule_id = None
    db.commit()
    response = admin_client.post(
        "/api/v1/sales",
        json={
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "tax-free-sale-0001",
            "payment_method": "CASH",
            "amount_tendered": "0.20",
            "items": [
                {"product_id": product.id, "quantity": 1, "unit_price": "0.20"}
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["tax_amount"] == 0
    assert response.json()["sale_items"][0]["tax_rule_id"] is None


def test_card_payment_is_not_accepted_without_provider(
    admin_client: TestClient, product, till, admin_user, open_pos_session
):
    session = open_pos_session(admin_user)
    response = admin_client.post(
        "/api/v1/sales",
        json={
            "till_id": till.id,
            "till_session_id": session.id,
            "idempotency_key": "card-sale-000001",
            "payment_method": "CARD",
            "amount_tendered": "10.00",
            "items": [
                {"product_id": product.id, "quantity": 1, "unit_price": "10.00"}
            ],
        },
    )

    assert response.status_code == 422

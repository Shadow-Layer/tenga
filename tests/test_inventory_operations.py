"""Sale-independent inventory operations integration tests."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.models.entities import (
    InventoryCount,
    InventoryMovement,
    InventoryTransfer,
    Location,
    Organization,
    Product,
    Sale,
    Stock,
    TaxRule,
)
from src.services.inventory_service import InventoryService


def _create_location(db, organization_id: int, code: str, name: str) -> Location:
    location = Location(
        organization_id=organization_id,
        code=code,
        name=name,
        is_active=True,
    )
    db.add(location)
    db.commit()
    return location


def test_receive_issue_transfer_count_reconcile_and_value_without_sales(
    authenticated_client: TestClient, db, org, product, location
):
    destination = _create_location(db, org.id, "LOC-DEST", "Destination")
    product.minimum_stock_level = 15
    db.commit()

    receipt_one = authenticated_client.post(
        "/api/v1/stock/stock/opening",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 10,
            "unit_cost": "2.00",
            "reason": "Supplier lot A",
        },
    )
    assert receipt_one.status_code == 201, receipt_one.text
    receipt_two = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 10,
            "unit_cost": "4.00",
            "reason": "Supplier lot B",
        },
    )
    assert receipt_two.status_code == 201, receipt_two.text
    first_movement = db.get(InventoryMovement, receipt_one.json()["id"])
    assert first_movement.unit_cost == Decimal("2.00")
    assert first_movement.currency_code == "USD"

    issue = authenticated_client.post(
        "/api/v1/stock/stock/issue",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 2,
            "reason": "Internal use",
        },
    )
    assert issue.status_code == 201, issue.text
    assert issue.json()["quantity"] == -2

    adjustment = authenticated_client.post(
        "/api/v1/stock/stock/adjust",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 1,
            "reason": "ADJUSTMENT",
        },
    )
    assert adjustment.status_code == 201, adjustment.text
    assert adjustment.json()["movement_type"] == "ADJUSTMENT"

    transfer = authenticated_client.post(
        "/api/v1/stock/stock/transfer",
        json={
            "source_location_id": location.id,
            "destination_location_id": destination.id,
            "reason": "Replenishment",
            "lines": [{"product_id": product.id, "quantity": 3}],
        },
    )
    assert transfer.status_code == 201, transfer.text
    assert transfer.json()["lines"] == [{"product_id": product.id, "quantity": 3}]

    movements_before_count = [
        (movement.id, movement.quantity, movement.created_at)
        for movement in db.query(InventoryMovement).order_by(InventoryMovement.id).all()
    ]
    count_response = authenticated_client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 15}],
        },
    )
    assert count_response.status_code == 201, count_response.text
    count = count_response.json()
    assert count["status"] == "DRAFT"
    assert count["lines"][0]["expected_quantity"] == 16
    assert count["lines"][0]["difference"] == -1

    reconciled = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count['id']}/reconcile",
        json={
            "expected_observations": [
                {
                    "product_id": line["product_id"],
                    "observed_quantity": line["observed_quantity"],
                }
                for line in count["lines"]
            ],
        },
    )
    assert reconciled.status_code == 200, reconciled.text
    assert reconciled.json()["status"] == "RECONCILED"
    assert reconciled.json()["lines"][0]["reconciled_movement_id"] is not None

    db.expire_all()
    source_balance = InventoryService.compute_stock_at_location(
        org.id, product.id, location.id, db
    )
    destination_balance = InventoryService.compute_stock_at_location(
        org.id, product.id, destination.id, db
    )
    assert (source_balance, destination_balance) == (15, 3)
    source_cache = db.query(Stock).filter_by(
        organization_id=org.id, product_id=product.id, location_id=location.id
    ).one()
    destination_cache = db.query(Stock).filter_by(
        organization_id=org.id,
        product_id=product.id,
        location_id=destination.id,
    ).one()
    assert (source_cache.quantity, destination_cache.quantity) == (15, 3)
    assert db.query(Sale).filter(Sale.organization_id == org.id).count() == 0
    destination_history = authenticated_client.get(
        "/api/v1/stock/stock/movements",
        params={"location_id": destination.id},
    )
    assert destination_history.status_code == 200, destination_history.text
    transfer_movement = next(
        movement
        for movement in destination_history.json()["items"]
        if movement["movement_type"] == "TRANSFER"
    )
    assert transfer_movement["location_id"] == location.id
    assert transfer_movement["to_location_id"] == destination.id

    movements_after_count = [
        (movement.id, movement.quantity, movement.created_at)
        for movement in db.query(InventoryMovement)
        .filter(InventoryMovement.id <= max(item[0] for item in movements_before_count))
        .order_by(InventoryMovement.id)
        .all()
    ]
    assert movements_after_count == movements_before_count
    correction = db.query(InventoryMovement).filter_by(
        reference_type="COUNT_RECONCILIATION",
        reference_id=count["id"],
    ).one()
    assert correction.quantity == -1

    valuation = authenticated_client.get("/api/v1/stock/stock/valuation")
    assert valuation.status_code == 200, valuation.text
    assert valuation.json()["currency_code"] == "USD"
    assert valuation.json()["total_value"] == "55.98"
    assert all(
        item["weighted_average_cost"] == "3.11"
        for item in valuation.json()["items"]
    )
    source_report = authenticated_client.get(
        f"/api/v1/stock/locations/{location.id}/report"
    )
    assert source_report.status_code == 200, source_report.text
    assert source_report.json()["total_value"] == "46.65"
    low_stock = authenticated_client.get("/api/v1/stock/stock/low-stock")
    assert low_stock.status_code == 200, low_stock.text
    assert any(
        item["location_id"] == location.id and item["quantity"] == 15
        for item in low_stock.json()["items"]
    )


def test_issue_rejects_insufficient_stock_and_transfer_is_role_restricted(
    client: TestClient, db, org, product, location
):
    destination = _create_location(db, org.id, "LOC-OTHER", "Other")
    response = client.post(
        "/api/v1/stock/stock/issue",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 1,
            "reason": "Usage",
        },
    )
    assert response.status_code == 409

    transfer = client.post(
        "/api/v1/stock/stock/transfer",
        json={
            "source_location_id": location.id,
            "destination_location_id": destination.id,
            "lines": [{"product_id": product.id, "quantity": 1}],
        },
    )
    assert transfer.status_code == 403

    count = client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 0}],
        },
    )
    assert count.status_code == 201, count.text
    reconcile = client.post(
        f"/api/v1/stock/stock/counts/{count.json()['id']}/reconcile",
        json={
            "expected_observations": [
                {
                    "product_id": line["product_id"],
                    "observed_quantity": line["observed_quantity"],
                }
                for line in count.json()["lines"]
            ],
        },
    )
    assert reconcile.status_code == 403


def test_cross_tenant_product_and_location_are_hidden(
    authenticated_client: TestClient, db, org, product, location
):
    other_org = Organization(name="Other tenant", code="OTHER")
    db.add(other_org)
    db.flush()
    foreign_location = Location(
        organization_id=other_org.id,
        code="FOREIGN",
        name="Foreign location",
        is_active=True,
    )
    foreign_product = Product(
        organization_id=other_org.id,
        sku="FOREIGN-SKU",
        name="Foreign product",
        price=Decimal("1.00"),
        cost=None,
        is_active=True,
    )
    db.add_all([foreign_location, foreign_product])
    db.commit()

    foreign_product_response = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": foreign_product.id,
            "location_id": location.id,
            "quantity": 1,
        },
    )
    foreign_location_response = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": foreign_location.id,
            "quantity": 1,
        },
    )
    assert foreign_product_response.status_code == 404
    assert foreign_location_response.status_code == 404
    cross_tenant_transfer = authenticated_client.post(
        "/api/v1/stock/stock/transfer",
        json={
            "source_location_id": location.id,
            "destination_location_id": foreign_location.id,
            "lines": [{"product_id": product.id, "quantity": 1}],
        },
    )
    assert cross_tenant_transfer.status_code == 404
    assert db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == other_org.id
    ).count() == 0

    foreign_tax = TaxRule(
        organization_id=other_org.id,
        name="Foreign VAT",
        rate=Decimal("15.00"),
        tax_inclusive=False,
        is_active=True,
    )
    db.add(foreign_tax)
    db.flush()
    product.tax_rule_id = foreign_tax.id
    db.commit()
    invalid_tax_link = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 1,
        },
    )
    assert invalid_tax_link.status_code == 409


def test_movement_idempotency_replay_and_conflicting_reuse(
    authenticated_client: TestClient, db, org, product, location
):
    payload = {
        "product_id": product.id,
        "location_id": location.id,
        "quantity": 7,
        "unit_cost": "2.50",
        "device_id": "device-1",
        "device_local_id": "event-1",
    }
    first = authenticated_client.post("/api/v1/stock/stock/receive", json=payload)
    replay = authenticated_client.post("/api/v1/stock/stock/receive", json=payload)
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert InventoryService.compute_stock_at_location(
        org.id, product.id, location.id, db
    ) == 7

    conflicting = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={**payload, "quantity": 8},
    )
    assert conflicting.status_code == 409
    assert db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == org.id
    ).count() == 1


def test_product_cost_and_organization_currency_are_snapshotted(
    authenticated_client: TestClient, db, org, product, location
):
    response = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 2,
        },
    )
    assert response.status_code == 201, response.text
    movement = db.get(InventoryMovement, response.json()["id"])
    assert movement.unit_cost == Decimal("5.00")
    assert movement.currency_code == org.currency_code == "USD"


def test_valuation_does_not_report_unknown_cost_stock_as_complete(
    authenticated_client: TestClient, db, org, location
):
    unknown_cost_product = Product(
        organization_id=org.id,
        sku="SKU-UNKNOWN-COST",
        name="Uncosted Item",
        price=Decimal("3.00"),
        cost=None,
        is_active=True,
    )
    db.add(unknown_cost_product)
    db.commit()
    received = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": unknown_cost_product.id,
            "location_id": location.id,
            "quantity": 4,
        },
    )
    assert received.status_code == 201, received.text

    organization_report = authenticated_client.get("/api/v1/stock/stock/valuation")
    assert organization_report.status_code == 200
    assert organization_report.json()["valuation_complete"] is False
    assert organization_report.json()["total_value"] is None

    location_report = authenticated_client.get(
        f"/api/v1/stock/locations/{location.id}/report"
    )
    assert location_report.status_code == 200
    assert location_report.json()["valuation_complete"] is False
    assert location_report.json()["total_value"] is None


def test_currencyless_legacy_organization_rejects_valued_movement(
    authenticated_client: TestClient, db, org, product, location
):
    org.currency_code = None
    db.commit()
    response = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 2,
            "unit_cost": "1.25",
        },
    )
    assert response.status_code == 409
    assert db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == org.id
    ).count() == 0
    assert org.currency_code is None


def test_count_reconciliation_conflicts_if_stock_changed_after_capture(
    authenticated_client: TestClient, db, org, product, location
):
    count_response = authenticated_client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 0}],
        },
    )
    assert count_response.status_code == 201
    count_id = count_response.json()["id"]
    receipt = authenticated_client.post(
        "/api/v1/stock/stock/receive",
        json={
            "product_id": product.id,
            "location_id": location.id,
            "quantity": 1,
        },
    )
    assert receipt.status_code == 201

    reconcile = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count_id}/reconcile",
        json={
            "expected_observations": [
                {
                    "product_id": line["product_id"],
                    "observed_quantity": line["observed_quantity"],
                }
                for line in count_response.json()["lines"]
            ],
        },
    )
    assert reconcile.status_code == 409
    count = db.get(InventoryCount, count_id)
    assert count.status == "DRAFT"
    assert db.query(InventoryMovement).filter_by(
        reference_type="COUNT_RECONCILIATION",
        reference_id=count_id,
    ).count() == 0


def test_count_detail_is_read_only_and_returns_current_server_observations(
    authenticated_client: TestClient, db, org, product, location
):
    created = authenticated_client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 4}],
        },
    )
    assert created.status_code == 201, created.text
    count_id = created.json()["id"]

    updated = authenticated_client.patch(
        f"/api/v1/stock/stock/counts/{count_id}",
        json={"lines": [{"product_id": product.id, "observed_quantity": 5}]},
    )
    assert updated.status_code == 200, updated.text

    detail = authenticated_client.get(f"/api/v1/stock/stock/counts/{count_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["lines"][0]["observed_quantity"] == 5

    unchanged = authenticated_client.get(f"/api/v1/stock/stock/counts/{count_id}")
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["lines"][0]["observed_quantity"] == 5
    assert db.query(InventoryMovement).filter_by(
        reference_type="COUNT_RECONCILIATION",
        reference_id=count_id,
    ).count() == 0


def test_count_reconciliation_rejects_observations_changed_since_review(
    authenticated_client: TestClient, db, org, product, location
):
    created = authenticated_client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 4}],
        },
    )
    assert created.status_code == 201, created.text
    count_id = created.json()["id"]
    reviewed_observations = [
        {"product_id": product.id, "observed_quantity": 4},
    ]

    updated = authenticated_client.patch(
        f"/api/v1/stock/stock/counts/{count_id}",
        json={"lines": [{"product_id": product.id, "observed_quantity": 5}]},
    )
    assert updated.status_code == 200, updated.text

    stale_reconcile = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count_id}/reconcile",
        json={"expected_observations": reviewed_observations},
    )
    assert stale_reconcile.status_code == 409, stale_reconcile.text
    assert db.get(InventoryCount, count_id).status == "DRAFT"
    assert db.query(InventoryMovement).filter_by(
        reference_type="COUNT_RECONCILIATION",
        reference_id=count_id,
    ).count() == 0

    current_reconcile = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count_id}/reconcile",
        json={"expected_observations": updated.json()["lines"]},
    )
    assert current_reconcile.status_code == 200, current_reconcile.text
    assert current_reconcile.json()["status"] == "RECONCILED"


def test_count_reconciliation_replay_returns_original_result_without_duplicate_movement(
    authenticated_client: TestClient, db, org, product, location
):
    created = authenticated_client.post(
        "/api/v1/stock/stock/counts",
        json={
            "location_id": location.id,
            "lines": [{"product_id": product.id, "observed_quantity": 4}],
        },
    )
    assert created.status_code == 201, created.text
    count = created.json()
    request = {
        "expected_observations": [
            {"product_id": product.id, "observed_quantity": 4},
        ],
    }

    first = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count['id']}/reconcile",
        json=request,
    )
    assert first.status_code == 200, first.text
    retry = authenticated_client.post(
        f"/api/v1/stock/stock/counts/{count['id']}/reconcile",
        json=request,
    )

    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "RECONCILED"
    assert retry.json()["lines"][0]["reconciled_movement_id"] == (
        first.json()["lines"][0]["reconciled_movement_id"]
    )
    assert db.query(InventoryMovement).filter_by(
        reference_type="COUNT_RECONCILIATION",
        reference_id=count["id"],
    ).count() == 1


def test_transfer_failure_rolls_back_header_movements_and_caches(
    authenticated_client: TestClient,
    db,
    org,
    product,
    location,
    monkeypatch,
):
    destination = _create_location(db, org.id, "LOC-ROLLBACK", "Rollback")
    second_product = Product(
        organization_id=org.id,
        sku="SKU-SECOND",
        name="Second Product",
        price=Decimal("1.00"),
        cost=None,
        is_active=True,
    )
    db.add(second_product)
    db.commit()
    for stock_product in (product, second_product):
        response = authenticated_client.post(
            "/api/v1/stock/stock/receive",
            json={
                "product_id": stock_product.id,
                "location_id": location.id,
                "quantity": 5,
            },
        )
        assert response.status_code == 201, response.text

    original_record = InventoryService.record_movement
    calls = 0

    def fail_second_movement(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated movement failure")
        return original_record(**kwargs)

    monkeypatch.setattr(
        InventoryService, "record_movement", staticmethod(fail_second_movement)
    )
    request = {
        "source_location_id": location.id,
        "destination_location_id": destination.id,
        "lines": [
            {"product_id": product.id, "quantity": 2},
            {"product_id": second_product.id, "quantity": 2},
        ],
    }
    with pytest.raises(RuntimeError, match="simulated movement failure"):
        authenticated_client.post("/api/v1/stock/stock/transfer", json=request)
    db.rollback()

    assert db.query(InventoryTransfer).filter(
        InventoryTransfer.organization_id == org.id
    ).count() == 0
    assert db.query(InventoryMovement).filter(
        InventoryMovement.reference_type == "TRANSFER"
    ).count() == 0
    assert InventoryService.compute_stock_at_location(
        org.id, product.id, location.id, db
    ) == 5
    assert InventoryService.compute_stock_at_location(
        org.id, product.id, destination.id, db
    ) == 0

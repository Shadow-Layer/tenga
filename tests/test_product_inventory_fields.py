from fastapi.testclient import TestClient

from src.models.entities import Organization


def test_product_create_and_update_persist_inventory_metadata(
    admin_client: TestClient,
    org: Organization,
):
    created = admin_client.post(
        "/api/v1/products",
        json={
            "organization_id": org.id,
            "sku": "UNIT-1",
            "name": "Boxed goods",
            "price": "4.50",
            "cost": "0",
            "unit_of_measure": "box",
            "minimum_stock_level": 6,
        },
    )

    assert created.status_code == 201
    assert created.json()["unit_of_measure"] == "box"
    assert created.json()["minimum_stock_level"] == 6
    product_id = created.json()["id"]

    updated = admin_client.put(
        f"/api/v1/products/{product_id}",
        json={"unit_of_measure": "case", "minimum_stock_level": 12},
    )

    assert updated.status_code == 200
    assert updated.json()["unit_of_measure"] == "case"
    assert updated.json()["minimum_stock_level"] == 12

    deactivated = admin_client.put(
        f"/api/v1/products/{product_id}",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    active_catalog = admin_client.get(
        "/api/v1/products",
        params={"organization_id": org.id},
    )
    full_catalog = admin_client.get(
        "/api/v1/products",
        params={"organization_id": org.id, "include_inactive": True},
    )
    assert active_catalog.json()["total"] == 0
    assert full_catalog.json()["total"] == 1


def test_product_rejects_empty_unit_and_negative_minimum(
    admin_client: TestClient,
    org: Organization,
):
    empty_unit = admin_client.post(
        "/api/v1/products",
        json={
            "organization_id": org.id,
            "sku": "UNIT-2",
            "name": "Invalid unit",
            "price": "1.00",
            "unit_of_measure": "   ",
        },
    )
    negative_minimum = admin_client.post(
        "/api/v1/products",
        json={
            "organization_id": org.id,
            "sku": "UNIT-3",
            "name": "Invalid minimum",
            "price": "1.00",
            "minimum_stock_level": -1,
        },
    )

    assert empty_unit.status_code == 422
    assert negative_minimum.status_code == 422


def test_product_response_defaults_inventory_metadata(admin_client: TestClient, org: Organization):
    created = admin_client.post(
        "/api/v1/products",
        json={
            "organization_id": org.id,
            "sku": "UNIT-4",
            "name": "Default unit",
            "price": "1.00",
        },
    )

    assert created.status_code == 201
    assert created.json()["unit_of_measure"] == "each"
    assert created.json()["minimum_stock_level"] == 0

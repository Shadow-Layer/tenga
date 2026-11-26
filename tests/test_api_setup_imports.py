from decimal import Decimal

from src.models.entities import DataImportBatch, InventoryMovement, Product, Sale, Stock


def test_product_import_preview_and_commit_are_admin_only(
    admin_client,
    client,
    org,
    db,
):
    csv_text = "sku,name,price,cost\nSKU-NEW,New product,12.50,5.00\n"
    preview = admin_client.post(
        "/api/v1/setup/imports/products/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["row_count"] == 1
    assert db.query(Product).filter_by(organization_id=org.id, sku="SKU-NEW").count() == 0

    denied = client.post(
        "/api/v1/setup/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert denied.status_code == 403

    committed = admin_client.post(
        "/api/v1/setup/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert committed.status_code == 200
    assert committed.json()["record_count"] == 1
    assert db.query(Product).filter_by(organization_id=org.id, sku="SKU-NEW").count() == 1
    assert db.query(DataImportBatch).filter_by(organization_id=org.id).count() == 1


def test_opening_inventory_import_reconciles_count_and_is_idempotent(
    admin_client,
    db,
    org,
    location,
    product,
):
    csv_text = f"sku,location_code,quantity\n{product.sku},{location.code},14\n"
    payload = {"csv_text": csv_text}

    preview = admin_client.post(
        "/api/v1/setup/imports/opening-inventory/preview",
        json=payload,
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True

    first = admin_client.post(
        "/api/v1/setup/imports/opening-inventory/commit",
        json=payload,
    )
    second = admin_client.post(
        "/api/v1/setup/imports/opening-inventory/commit",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["already_imported"] is True
    assert db.query(Stock).filter_by(
        organization_id=org.id,
        product_id=product.id,
        location_id=location.id,
    ).one().quantity == 14
    assert db.query(InventoryMovement).filter_by(
        organization_id=org.id,
        product_id=product.id,
        location_id=location.id,
    ).count() == 1

    equivalent_count = admin_client.post(
        "/api/v1/setup/imports/opening-inventory/commit",
        json={"csv_text": f"SKU,location_code,quantity\n{product.sku},{location.code},14\n"},
    )
    assert equivalent_count.status_code == 200
    assert db.query(InventoryMovement).filter_by(
        organization_id=org.id,
        product_id=product.id,
        location_id=location.id,
    ).count() == 1


def test_historical_sales_import_does_not_change_stock(
    admin_client,
    db,
    org,
    till,
    product,
):
    csv_text = (
        "receipt_id,sold_at,sku,quantity,unit_price,discount_per_item,"
        "tax_rate,tax_inclusive,payment_method\n"
        "OLD-100,2025-01-02T10:00:00+02:00,SKU001,2,10.00,1.00,15.00,false,CASH\n"
        "OLD-100,2025-01-02T10:00:00+02:00,SKU001,1,10.00,0.00,15.00,false,CASH\n"
    )
    response = admin_client.post(
        "/api/v1/setup/imports/historical-sales/commit",
        json={
            "csv_text": csv_text,
            "default_till_id": till.id,
        },
    )

    assert response.status_code == 200, response.text
    sale = db.query(Sale).filter_by(
        organization_id=org.id,
        external_reference="OLD-100",
    ).one()
    assert sale.source_type == "HISTORICAL_IMPORT"
    assert sale.total_amount == Decimal("32.20")
    assert sale.discount_amount == Decimal("2.00")
    assert sale.tax_amount == Decimal("4.20")
    assert len(sale.sale_items) == 2
    assert db.query(InventoryMovement).filter_by(
        organization_id=org.id,
        product_id=product.id,
    ).count() == 0

    same_file_retry = admin_client.post(
        "/api/v1/setup/imports/historical-sales/commit",
        json={
            "csv_text": csv_text,
            "default_till_id": till.id,
        },
    )
    assert same_file_retry.status_code == 200
    assert same_file_retry.json()["already_imported"] is True

    duplicate_reference = admin_client.post(
        "/api/v1/setup/imports/historical-sales/commit",
        json={
            "csv_text": csv_text.replace("10.00", "11.00", 1),
            "default_till_id": till.id,
        },
    )
    assert duplicate_reference.status_code == 422
    assert db.query(Sale).filter_by(
        organization_id=org.id,
        source_type="HISTORICAL_IMPORT",
    ).count() == 1

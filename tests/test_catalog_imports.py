"""Isolated API tests for catalog CSV workflows."""
import csv
import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.config import Base, get_db
from src.main import app
from src.models.entities import (
    DataImportBatch,
    InventoryMovement,
    Location,
    Organization,
    Product,
    Stock,
    User,
)
from src.security.auth import create_access_token
from src.security.password import hash_password


@pytest.fixture
def catalog_api():
    """Use a private in-memory database; never open or mutate the configured DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = test_session()

    organization = Organization(name="Catalog Test", code="CATALOG")
    db.add(organization)
    db.flush()
    admin = User(
        organization_id=organization.id,
        email="catalog-admin@test.invalid",
        username="catalog-admin",
        full_name="Catalog Admin",
        password_hash=hash_password("test-password"),
        role="admin",
    )
    location = Location(
        organization_id=organization.id,
        code="MAIN",
        name="Main Store",
        is_active=True,
    )
    db.add_all([admin, location])
    db.commit()
    token = create_access_token(
        user_id=admin.id,
        email=admin.email,
        organization_id=organization.id,
        username=admin.username,
        role=admin.role,
    )

    def override_get_db():
        yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    client.headers["Authorization"] = f"Bearer {token}"
    try:
        yield {
            "client": client,
            "db": db,
            "organization": organization,
            "admin": admin,
            "location": location,
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _product(db, organization_id, sku, **kwargs):
    product = Product(
        organization_id=organization_id,
        sku=sku,
        name=kwargs.pop("name", sku),
        price=kwargs.pop("price", Decimal("3.50")),
        cost=kwargs.pop("cost", Decimal("1.25")),
        is_active=True,
        **kwargs,
    )
    db.add(product)
    db.commit()
    return product


def test_templates_export_and_import_history_are_tenant_scoped(catalog_api):
    client = catalog_api["client"]
    db = catalog_api["db"]
    organization = catalog_api["organization"]
    product = _product(
        db,
        organization.id,
        "LOCAL-1",
        name="Local, item",
        unit_of_measure="carton",
        minimum_stock_level=7,
    )

    template = client.get("/api/v1/products/imports/template")
    assert template.status_code == 200
    template_headers = next(csv.reader(io.StringIO(template.text)))
    assert "unit_of_measure" in template_headers
    assert "minimum_stock_level" in template_headers
    stock_template = client.get("/api/v1/products/imports/opening-stock/template")
    assert stock_template.status_code == 200
    assert stock_template.text == "sku,location_code,quantity\r\n"

    other_org = Organization(name="Other Catalog", code="OTHER-CATALOG")
    db.add(other_org)
    db.flush()
    other_product = Product(
        organization_id=other_org.id,
        sku="OTHER-1",
        name="Other product",
        price=Decimal("2.00"),
        is_active=True,
    )
    db.add(other_product)
    db.commit()

    exported = client.get("/api/v1/products/export")
    assert exported.status_code == 200
    exported_rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert [row["sku"] for row in exported_rows] == [product.sku]
    assert exported_rows[0]["name"] == product.name
    assert exported_rows[0]["unit_of_measure"] == "carton"
    assert exported_rows[0]["minimum_stock_level"] == "7"

    round_trip_rows = list(csv.DictReader(io.StringIO(exported.text)))
    round_trip_rows[0]["sku"] = "ROUND-TRIP-1"
    round_trip = io.StringIO(newline="")
    writer = csv.DictWriter(round_trip, fieldnames=round_trip_rows[0].keys())
    writer.writeheader()
    writer.writerows(round_trip_rows)
    imported = client.post(
        "/api/v1/products/imports/products/commit",
        json={"csv_text": round_trip.getvalue()},
    )
    assert imported.status_code == 200
    imported_product = db.query(Product).filter_by(
        organization_id=organization.id, sku="ROUND-TRIP-1"
    ).one()
    assert imported_product.unit_of_measure == "carton"
    assert imported_product.minimum_stock_level == 7

    history = client.get("/api/v1/products/imports")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["row_count"] == 1


def test_product_preview_commit_retry_and_history(catalog_api):
    client = catalog_api["client"]
    db = catalog_api["db"]
    organization = catalog_api["organization"]
    csv_text = (
        "SKU,Name,Price,Cost,Unit_of_Measure,Minimum_Stock_Level,Barcode,Category,Description\n"
        'NEW-1,"New, item",12.50,5.25,pack,4,12345,Food,"Imported item"\n'
    )

    preview = client.post(
        "/api/v1/products/imports/products/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["row_count"] == 1
    assert preview.json()["rows"][0]["name"] == "New, item"
    assert preview.json()["rows"][0]["unit_of_measure"] == "pack"
    assert preview.json()["rows"][0]["minimum_stock_level"] == 4
    assert db.query(Product).filter_by(
        organization_id=organization.id, sku="NEW-1"
    ).count() == 0

    committed = client.post(
        "/api/v1/products/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert committed.status_code == 200
    assert committed.json()["record_count"] == 1
    assert committed.json()["already_imported"] is False
    retry = client.post(
        "/api/v1/products/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert retry.status_code == 200
    assert retry.json()["already_imported"] is True
    assert db.query(Product).filter_by(
        organization_id=organization.id, sku="NEW-1"
    ).count() == 1
    imported_product = db.query(Product).filter_by(
        organization_id=organization.id, sku="NEW-1"
    ).one()
    assert imported_product.unit_of_measure == "pack"
    assert imported_product.minimum_stock_level == 4
    assert db.query(DataImportBatch).filter_by(
        organization_id=organization.id, import_type="catalog_products"
    ).count() == 1

    history = client.get("/api/v1/products/imports")
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["row_count"] == 1


def test_product_validation_reports_duplicates_and_commits_nothing(catalog_api):
    client = catalog_api["client"]
    db = catalog_api["db"]
    organization = catalog_api["organization"]
    _product(db, organization.id, "EXISTING", barcode="old-barcode")
    csv_text = (
        "sku,name,price,unit_of_measure,minimum_stock_level,barcode\n"
        "GOOD-1,Valid product,4.00,each,0,new-barcode\n"
        "GOOD-1,Duplicate SKU,5.00,each,0,second-barcode\n"
        "NEW-2,Duplicate barcode,6.00,each,0,old-barcode\n"
        "BAD-PRICE,Bad price,not-a-price,each,0,\n"
    )

    preview = client.post(
        "/api/v1/products/imports/products/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is False
    assert {(error["row_number"], error["field"]) for error in preview.json()["errors"]} >= {
        (3, "sku"),
        (4, "barcode"),
        (5, "price"),
    }

    commit = client.post(
        "/api/v1/products/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert commit.status_code == 422
    assert db.query(Product).filter_by(
        organization_id=organization.id, sku="GOOD-1"
    ).count() == 0
    assert db.query(DataImportBatch).filter_by(
        organization_id=organization.id
    ).count() == 0


@pytest.mark.parametrize(
    ("unit_of_measure", "minimum_stock_level", "expected_error"),
    [
        ("", "0", "unit_of_measure"),
        ("x" * 51, "0", "unit_of_measure"),
        ("each", "-1", "minimum_stock_level"),
        ("each", "1.5", "minimum_stock_level"),
        ("each", "", "minimum_stock_level"),
    ],
)
def test_product_import_validates_unit_and_minimum_stock_level(
    catalog_api, unit_of_measure, minimum_stock_level, expected_error
):
    client = catalog_api["client"]
    csv_text = (
        "sku,name,price,unit_of_measure,minimum_stock_level\n"
        f"SKU-1,Example,2.50,{unit_of_measure},{minimum_stock_level}\n"
    )

    preview = client.post(
        "/api/v1/products/imports/products/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is False
    assert any(error["field"] == expected_error for error in preview.json()["errors"])

    commit = client.post(
        "/api/v1/products/imports/products/commit",
        json={"csv_text": csv_text},
    )
    assert commit.status_code == 422
    assert catalog_api["db"].query(Product).filter_by(sku="SKU-1").count() == 0


def test_opening_stock_import_is_atomic_scoped_and_idempotent(catalog_api):
    client = catalog_api["client"]
    db = catalog_api["db"]
    organization = catalog_api["organization"]
    location = catalog_api["location"]
    product = _product(db, organization.id, "STOCK-1")
    csv_text = f"sku,location_code,quantity\n{product.sku},{location.code},14\n"

    preview = client.post(
        "/api/v1/products/imports/opening-stock/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["rows"][0]["quantity"] == 14

    first = client.post(
        "/api/v1/products/imports/opening-stock/commit",
        json={"csv_text": csv_text},
    )
    retry = client.post(
        "/api/v1/products/imports/opening-stock/commit",
        json={"csv_text": csv_text},
    )
    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["already_imported"] is True
    assert db.query(Stock).filter_by(
        organization_id=organization.id,
        product_id=product.id,
        location_id=location.id,
    ).one().quantity == 14
    assert db.query(InventoryMovement).filter_by(
        organization_id=organization.id,
        product_id=product.id,
        location_id=location.id,
    ).count() == 1

    updated_opening_balance = client.post(
        "/api/v1/products/imports/opening-stock/commit",
        json={"csv_text": f"sku,location_code,quantity\n{product.sku},{location.code},18\n"},
    )
    assert updated_opening_balance.status_code == 200
    assert db.query(Stock).filter_by(
        organization_id=organization.id,
        product_id=product.id,
        location_id=location.id,
    ).one().quantity == 18
    assert db.query(InventoryMovement).filter_by(
        organization_id=organization.id,
        product_id=product.id,
        location_id=location.id,
    ).count() == 2


def test_opening_stock_row_errors_prevent_partial_commit(catalog_api):
    client = catalog_api["client"]
    db = catalog_api["db"]
    organization = catalog_api["organization"]
    location = catalog_api["location"]
    product = _product(db, organization.id, "STOCK-2")
    csv_text = (
        "sku,location_code,quantity\n"
        f"{product.sku},{location.code},7\n"
        f"{product.sku},{location.code},9\n"
        "MISSING,UNKNOWN,-2\n"
    )

    preview = client.post(
        "/api/v1/products/imports/opening-stock/preview",
        json={"csv_text": csv_text},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is False
    assert preview.json()["valid_count"] == 1
    assert len(preview.json()["rows"]) == 1
    assert len(preview.json()["errors"]) >= 3

    commit = client.post(
        "/api/v1/products/imports/opening-stock/commit",
        json={"csv_text": csv_text},
    )
    assert commit.status_code == 422
    assert db.query(Stock).filter_by(
        organization_id=organization.id,
        product_id=product.id,
        location_id=location.id,
    ).count() == 0
    assert db.query(InventoryMovement).filter_by(
        organization_id=organization.id,
        product_id=product.id,
    ).count() == 0
    assert db.query(DataImportBatch).filter_by(
        organization_id=organization.id
    ).count() == 0


def test_catalog_imports_require_admin_role(catalog_api):
    client = catalog_api["client"]
    catalog_api["admin"].role = "operator"
    catalog_api["db"].commit()

    response = client.post(
        "/api/v1/products/imports/products/preview",
        json={
            "csv_text": (
                "sku,name,price,unit_of_measure,minimum_stock_level\n"
                "NEW,New product,2.00,each,0\n"
            )
        },
    )
    assert response.status_code == 403

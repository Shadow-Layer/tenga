"""Tenant-scoped CSV validation and atomic catalog import operations."""
import csv
import hashlib
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

from sqlalchemy import func, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.entities import (
    DataImportBatch,
    InventoryMovement,
    Location,
    Product,
    TaxRule,
    User,
)
from src.services.inventory_service import InventoryService

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MAX_PREVIEW_ROWS = 100
MAX_PREVIEW_ERRORS = 200
MONEY = Decimal("0.01")
MAX_MONEY = Decimal("9999999999.99")
PRODUCT_IMPORT_TYPE = "catalog_products"
OPENING_STOCK_IMPORT_TYPE = "opening_stock"

PRODUCT_HEADERS = {
    "sku",
    "name",
    "price",
    "cost",
    "unit_of_measure",
    "minimum_stock_level",
    "barcode",
    "category",
    "description",
    "tax_rule_id",
}
OPENING_STOCK_HEADERS = {"sku", "location_code", "quantity"}


class CatalogImportFailure(Exception):
    """Expected import failure with an HTTP status and API-safe detail."""

    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class CatalogImportService:
    """Validates CSV data and commits each import in a single transaction."""

    @staticmethod
    def _parse_csv(
        csv_text: str,
        required_headers: set[str],
        allowed_headers: set[str],
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]], int]:
        if len(csv_text.encode("utf-8")) > MAX_IMPORT_BYTES:
            raise CatalogImportFailure(413, "CSV file exceeds the 5 MB limit.")

        errors: list[dict[str, Any]] = []
        rows: list[dict[str, str]] = []
        stream = io.StringIO(csv_text.lstrip("\ufeff"), newline="")
        reader = csv.reader(stream, strict=True)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return [], [{"row_number": 1, "field": "csv", "message": "CSV must include a header row."}], 0
        except csv.Error as error:
            return [], [{"row_number": 1, "field": "csv", "message": f"Invalid CSV: {error}."}], 0

        headers = [header.strip().casefold() for header in raw_headers]
        if not headers or any(not header for header in headers):
            errors.append({"row_number": 1, "field": "header", "message": "Headers must not be empty."})
        if len(set(headers)) != len(headers):
            errors.append({"row_number": 1, "field": "header", "message": "Headers must be unique."})
        for header in sorted(required_headers - set(headers)):
            errors.append(
                {"row_number": 1, "field": header, "message": f"Required column '{header}' is missing."}
            )
        for header in sorted(set(headers) - allowed_headers):
            errors.append(
                {"row_number": 1, "field": header, "message": f"Unexpected column '{header}'."}
            )
        if errors:
            return [], errors, 0

        try:
            for line_number, values in enumerate(reader, start=2):
                if not values:
                    continue
                if len(rows) >= MAX_IMPORT_ROWS:
                    raise CatalogImportFailure(413, "CSV exceeds the 5,000-row limit.")
                row = {
                    header: (values[index].strip() if index < len(values) else "")
                    for index, header in enumerate(headers)
                }
                if len(values) != len(headers):
                    row["__error__"] = (
                        f"Row has {len(values)} values; expected {len(headers)}."
                    )
                row["__row_number__"] = str(line_number)
                rows.append(row)
        except csv.Error as error:
            errors.append(
                {
                    "row_number": len(rows) + 2,
                    "field": "csv",
                    "message": f"Invalid CSV: {error}.",
                }
            )

        if not rows and not errors:
            errors.append(
                {"row_number": 1, "field": "csv", "message": "CSV must include at least one data row."}
            )
        return rows, errors, len(rows)

    @staticmethod
    def _money(value: str, field: str, minimum: Decimal) -> Decimal:
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field} must be a number.")
        if not parsed.is_finite() or parsed < minimum or parsed > MAX_MONEY:
            raise ValueError(f"{field} must be between {minimum} and {MAX_MONEY}.")
        if max(0, -parsed.as_tuple().exponent) > 2:
            raise ValueError(f"{field} must have no more than two decimal places.")
        return parsed.quantize(MONEY, rounding=ROUND_HALF_UP)

    @staticmethod
    def _preview(
        rows: list[dict[str, Any]],
        errors: list[dict[str, Any]],
        row_count: int,
        already_imported: bool = False,
    ) -> dict[str, Any]:
        return {
            "valid": not errors,
            "already_imported": already_imported,
            "row_count": row_count,
            "valid_count": max(0, row_count - len({error["row_number"] for error in errors if error["row_number"] > 1})),
            "errors": errors[:MAX_PREVIEW_ERRORS],
            "truncated_errors": max(0, len(errors) - MAX_PREVIEW_ERRORS),
            "rows": rows[:MAX_PREVIEW_ROWS],
            "truncated_rows": max(0, len(rows) - MAX_PREVIEW_ROWS),
        }

    @classmethod
    def validate_products(
        cls, csv_text: str, organization_id: int, db: Session
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        source_rows, errors, row_count = cls._parse_csv(
            csv_text,
            {"sku", "name", "price", "unit_of_measure", "minimum_stock_level"},
            PRODUCT_HEADERS,
        )
        if errors:
            return cls._preview([], errors, row_count), []

        existing_products = db.query(Product).filter(
            Product.organization_id == organization_id
        ).all()
        existing_skus = {product.sku.casefold() for product in existing_products}
        existing_barcodes = {
            product.barcode.casefold()
            for product in existing_products
            if product.barcode
        }
        seen_skus: set[str] = set()
        seen_barcodes: set[str] = set()
        normalized: list[dict[str, Any]] = []

        for source in source_rows:
            line = int(source["__row_number__"])
            row_errors: list[dict[str, Any]] = []
            if "__error__" in source:
                row_errors.append({"row_number": line, "field": "csv", "message": source["__error__"]})

            sku = source.get("sku", "").strip()
            name = source.get("name", "").strip()
            sku_key = sku.casefold()
            if not sku or len(sku) > 100:
                row_errors.append(
                    {"row_number": line, "field": "sku", "message": "SKU is required and must be at most 100 characters."}
                )
            elif sku_key in seen_skus:
                row_errors.append(
                    {"row_number": line, "field": "sku", "message": f"Duplicate SKU '{sku}' in this file."}
                )
            elif sku_key in existing_skus:
                row_errors.append(
                    {"row_number": line, "field": "sku", "message": f"SKU '{sku}' already exists in this organization."}
                )
            else:
                seen_skus.add(sku_key)

            if not name or len(name) > 255:
                row_errors.append(
                    {"row_number": line, "field": "name", "message": "Name is required and must be at most 255 characters."}
                )

            unit_of_measure = source.get("unit_of_measure", "").strip()
            if not unit_of_measure:
                row_errors.append(
                    {"row_number": line, "field": "unit_of_measure", "message": "Unit of measure is required."}
                )
            elif len(unit_of_measure) > 50:
                row_errors.append(
                    {"row_number": line, "field": "unit_of_measure", "message": "Unit of measure must be at most 50 characters."}
                )

            minimum_stock_level: Optional[int] = None
            minimum_stock_value = source.get("minimum_stock_level", "")
            try:
                minimum_stock_level = int(minimum_stock_value)
                if minimum_stock_level < 0:
                    raise ValueError
            except ValueError:
                row_errors.append(
                    {
                        "row_number": line,
                        "field": "minimum_stock_level",
                        "message": "Minimum stock level must be a whole number greater than or equal to zero.",
                    }
                )

            price: Optional[Decimal] = None
            try:
                price = cls._money(source.get("price", ""), "price", Decimal("0.01"))
            except ValueError as error:
                row_errors.append({"row_number": line, "field": "price", "message": str(error)})

            cost: Optional[Decimal] = None
            if source.get("cost"):
                try:
                    cost = cls._money(source["cost"], "cost", Decimal("0"))
                except ValueError as error:
                    row_errors.append({"row_number": line, "field": "cost", "message": str(error)})

            barcode = source.get("barcode", "").strip() or None
            if barcode and len(barcode) > 100:
                row_errors.append(
                    {"row_number": line, "field": "barcode", "message": "Barcode must be at most 100 characters."}
                )
            elif barcode:
                barcode_key = barcode.casefold()
                if barcode_key in seen_barcodes or barcode_key in existing_barcodes:
                    row_errors.append(
                        {"row_number": line, "field": "barcode", "message": f"Barcode '{barcode}' is already in use."}
                    )
                else:
                    seen_barcodes.add(barcode_key)

            category = source.get("category", "").strip() or None
            if category and len(category) > 100:
                row_errors.append(
                    {"row_number": line, "field": "category", "message": "Category must be at most 100 characters."}
                )
            description = source.get("description", "").strip() or None
            if description and len(description) > 1000:
                row_errors.append(
                    {"row_number": line, "field": "description", "message": "Description must be at most 1000 characters."}
                )

            tax_rule_id: Optional[int] = None
            tax_rule_value = source.get("tax_rule_id", "")
            if tax_rule_value:
                try:
                    tax_rule_id = int(tax_rule_value)
                except ValueError:
                    row_errors.append(
                        {"row_number": line, "field": "tax_rule_id", "message": "Tax rule ID must be a whole number."}
                    )
                if tax_rule_id is not None and not db.query(TaxRule).filter(
                    TaxRule.id == tax_rule_id,
                    TaxRule.organization_id == organization_id,
                    TaxRule.is_active.is_(True),
                ).first():
                    row_errors.append(
                        {"row_number": line, "field": "tax_rule_id", "message": f"Active tax rule '{tax_rule_id}' was not found in this organization."}
                    )

            if not row_errors:
                normalized_row = {
                    "source_row": line,
                    "sku": sku,
                    "name": name,
                    "price": price,
                    "cost": cost,
                    "unit_of_measure": unit_of_measure,
                    "minimum_stock_level": minimum_stock_level,
                    "barcode": barcode,
                    "category": category,
                    "description": description,
                    "tax_rule_id": tax_rule_id,
                }
                normalized.append(normalized_row)
            errors.extend(row_errors)

        preview_rows = [
            {
                "row_number": row["source_row"],
                "sku": row["sku"],
                "name": row["name"],
                "price": row["price"],
                "cost": row["cost"],
                "unit_of_measure": row["unit_of_measure"],
                "minimum_stock_level": row["minimum_stock_level"],
                "barcode": row["barcode"],
                "category": row["category"],
                "description": row["description"],
                "tax_rule_id": row["tax_rule_id"],
            }
            for row in normalized
        ]
        result = cls._preview(preview_rows, errors, row_count)
        result["valid_count"] = len(normalized)
        return result, normalized

    @classmethod
    def validate_opening_stock(
        cls, csv_text: str, organization_id: int, db: Session
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        source_rows, errors, row_count = cls._parse_csv(
            csv_text, OPENING_STOCK_HEADERS, OPENING_STOCK_HEADERS
        )
        if errors:
            return cls._preview([], errors, row_count), []

        products = {
            product.sku.casefold(): product
            for product in db.query(Product).filter(
                Product.organization_id == organization_id,
                Product.is_active.is_(True),
            ).all()
        }
        locations = {
            location.code.casefold(): location
            for location in db.query(Location).filter(
                Location.organization_id == organization_id,
                Location.is_active.is_(True),
            ).all()
        }
        seen_pairs: set[tuple[str, str]] = set()
        normalized: list[dict[str, Any]] = []

        for source in source_rows:
            line = int(source["__row_number__"])
            row_errors: list[dict[str, Any]] = []
            if "__error__" in source:
                row_errors.append({"row_number": line, "field": "csv", "message": source["__error__"]})
            sku = source.get("sku", "").strip()
            location_code = source.get("location_code", "").strip()
            product = products.get(sku.casefold())
            location = locations.get(location_code.casefold())
            if product is None:
                row_errors.append(
                    {"row_number": line, "field": "sku", "message": f"Active product SKU '{sku}' was not found in this organization."}
                )
            if location is None:
                row_errors.append(
                    {"row_number": line, "field": "location_code", "message": f"Active location '{location_code}' was not found in this organization."}
                )
            pair_key = (sku.casefold(), location_code.casefold())
            if pair_key in seen_pairs:
                row_errors.append(
                    {"row_number": line, "field": "sku", "message": "Duplicate product/location pair in this file."}
                )
            else:
                seen_pairs.add(pair_key)

            quantity: Optional[int] = None
            try:
                raw_quantity = source.get("quantity", "")
                quantity = int(raw_quantity)
                if quantity < 0:
                    raise ValueError
            except ValueError:
                row_errors.append(
                    {"row_number": line, "field": "quantity", "message": "Quantity must be a whole number greater than or equal to zero."}
                )

            if (
                product is not None
                and location is not None
                and quantity is not None
                and quantity >= 0
                and not row_errors
            ):
                normalized.append(
                    {
                        "source_row": line,
                        "sku": product.sku,
                        "product_id": product.id,
                        "location_code": location.code,
                        "location_id": location.id,
                        "quantity": quantity,
                        "reason": "OPENING_BALANCE",
                    }
                )
            errors.extend(row_errors)

        preview_rows = [
            {
                "row_number": row["source_row"],
                "sku": row["sku"],
                "location_code": row["location_code"],
                "quantity": row["quantity"],
            }
            for row in normalized
        ]
        result = cls._preview(preview_rows, errors, row_count)
        result["valid_count"] = len(normalized)
        return result, normalized

    @staticmethod
    def _content_hash(csv_text: str) -> str:
        return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()

    @classmethod
    def _existing_batch(
        cls, csv_text: str, organization_id: int, import_type: str, db: Session
    ) -> Optional[DataImportBatch]:
        return db.query(DataImportBatch).filter(
            DataImportBatch.organization_id == organization_id,
            DataImportBatch.import_type == import_type,
            DataImportBatch.content_sha256 == cls._content_hash(csv_text),
        ).first()

    @classmethod
    def _commit(
        cls,
        import_type: str,
        csv_text: str,
        organization_id: int,
        current_user: User,
        db: Session,
        validator,
    ) -> dict[str, Any]:
        existing = cls._existing_batch(csv_text, organization_id, import_type, db)
        if existing:
            return {
                "batch_id": existing.id,
                "record_count": existing.row_count,
                "already_imported": True,
            }

        preview, rows = validator(csv_text, organization_id, db)
        if not preview["valid"]:
            raise CatalogImportFailure(
                422,
                {"message": "Import has validation errors.", "preview": preview},
            )

        batch = DataImportBatch(
            organization_id=organization_id,
            created_by_id=current_user.id,
            import_type=import_type,
            content_sha256=cls._content_hash(csv_text),
            row_count=preview["row_count"],
        )
        try:
            db.add(batch)
            db.flush()
            if import_type == PRODUCT_IMPORT_TYPE:
                for row in rows:
                    db.add(
                        Product(
                            organization_id=organization_id,
                            sku=row["sku"],
                            name=row["name"],
                            price=row["price"],
                            cost=row["cost"],
                            unit_of_measure=row["unit_of_measure"],
                            minimum_stock_level=row["minimum_stock_level"],
                            barcode=row["barcode"],
                            category=row["category"],
                            description=row["description"],
                            tax_rule_id=row["tax_rule_id"],
                            is_active=True,
                        )
                    )
            else:
                pairs = [(row["product_id"], row["location_id"]) for row in rows]
                movement_totals = {
                    (product_id, location_id): quantity
                    for product_id, location_id, quantity in db.query(
                        InventoryMovement.product_id,
                        InventoryMovement.location_id,
                        func.coalesce(func.sum(InventoryMovement.quantity), 0),
                    ).filter(
                        InventoryMovement.organization_id == organization_id,
                        tuple_(
                            InventoryMovement.product_id,
                            InventoryMovement.location_id,
                        ).in_(pairs),
                    ).group_by(
                        InventoryMovement.product_id,
                        InventoryMovement.location_id,
                    ).all()
                } if pairs else {}
                for row in rows:
                    current_quantity = movement_totals.get(
                        (row["product_id"], row["location_id"]), 0
                    )
                    delta = row["quantity"] - current_quantity
                    if delta:
                        InventoryService.record_movement(
                            organization_id=organization_id,
                            product_id=row["product_id"],
                            location_id=row["location_id"],
                            quantity=delta,
                            reason=row["reason"],
                            recorded_by_id=current_user.id,
                            reference_type="OPENING_IMPORT",
                            reference_id=batch.id,
                            db=db,
                            commit=False,
                        )
                    InventoryService.update_stock_cache(
                        organization_id,
                        row["product_id"],
                        row["location_id"],
                        db,
                        commit=False,
                    )
            db.commit()
            db.refresh(batch)
            return {
                "batch_id": batch.id,
                "record_count": preview["row_count"],
                "already_imported": False,
            }
        except IntegrityError as error:
            db.rollback()
            duplicate = cls._existing_batch(
                csv_text, organization_id, import_type, db
            )
            if duplicate:
                return {
                    "batch_id": duplicate.id,
                    "record_count": duplicate.row_count,
                    "already_imported": True,
                }
            raise CatalogImportFailure(
                409,
                "Catalog data changed during import; no records were committed. Preview the CSV and retry.",
            ) from error
        except Exception:
            db.rollback()
            raise

    @classmethod
    def commit_products(
        cls, csv_text: str, organization_id: int, current_user: User, db: Session
    ) -> dict[str, Any]:
        return cls._commit(
            PRODUCT_IMPORT_TYPE,
            csv_text,
            organization_id,
            current_user,
            db,
            cls.validate_products,
        )

    @classmethod
    def commit_opening_stock(
        cls, csv_text: str, organization_id: int, current_user: User, db: Session
    ) -> dict[str, Any]:
        return cls._commit(
            OPENING_STOCK_IMPORT_TYPE,
            csv_text,
            organization_id,
            current_user,
            db,
            cls.validate_opening_stock,
        )

    @staticmethod
    def product_template() -> str:
        output = io.StringIO(newline="")
        csv.writer(output).writerow(
            [
                "sku",
                "name",
                "price",
                "cost",
                "unit_of_measure",
                "minimum_stock_level",
                "barcode",
                "category",
                "description",
                "tax_rule_id",
            ]
        )
        return output.getvalue()

    @staticmethod
    def export_products(organization_id: int, db: Session) -> str:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "sku",
                "name",
                "price",
                "cost",
                "unit_of_measure",
                "minimum_stock_level",
                "barcode",
                "category",
                "description",
                "tax_rule_id",
            ]
        )
        products = db.query(Product).filter(
            Product.organization_id == organization_id
        ).order_by(Product.sku, Product.id).all()
        for product in products:
            writer.writerow(
                [
                    product.sku,
                    product.name,
                    f"{product.price:.2f}",
                    f"{product.cost:.2f}" if product.cost is not None else "",
                    product.unit_of_measure,
                    product.minimum_stock_level,
                    product.barcode or "",
                    product.category or "",
                    product.description or "",
                    product.tax_rule_id or "",
                ]
            )
        return output.getvalue()

    @staticmethod
    def import_history(
        organization_id: int, skip: int, limit: int, db: Session
    ) -> tuple[list[DataImportBatch], int]:
        query = db.query(DataImportBatch).filter(
            DataImportBatch.organization_id == organization_id,
            DataImportBatch.import_type.in_(
                [PRODUCT_IMPORT_TYPE, OPENING_STOCK_IMPORT_TYPE]
            ),
        )
        total = query.count()
        items = query.order_by(
            DataImportBatch.created_at.desc(), DataImportBatch.id.desc()
        ).offset(skip).limit(limit).all()
        return items, total

    @classmethod
    def import_status(
        cls, csv_text: str, organization_id: int, import_type: str, db: Session
    ) -> Optional[DataImportBatch]:
        return cls._existing_batch(csv_text, organization_id, import_type, db)

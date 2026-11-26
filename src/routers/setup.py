"""Admin-only CSV imports used by the initial setup wizard."""
import csv
import hashlib
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import (
    DataImportBatch,
    InventoryMovement,
    Location,
    Product,
    Sale,
    SaleItem,
    TaxRule,
    Till,
    User,
)
from src.security.authorization import get_current_user
from src.services.inventory_service import InventoryService

router = APIRouter()

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
MONEY = Decimal("0.01")


class CSVImportRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)
    default_till_id: Optional[int] = Field(None, gt=0)
    default_cashier_id: Optional[int] = Field(None, gt=0)


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can run setup imports.")


def _parse_csv(csv_text: str) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    if len(csv_text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 5 MB limit.")
    try:
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")), strict=True)
        if not reader.fieldnames:
            raise HTTPException(status_code=422, detail="CSV must include a header row.")
        headers = [header.strip().lower() for header in reader.fieldnames if header]
        if len(headers) != len(reader.fieldnames) or len(set(headers)) != len(headers):
            raise HTTPException(status_code=422, detail="CSV headers must be non-empty and unique.")
        rows: list[tuple[int, dict[str, str]]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                rows.append((line_number, {"__error__": "Row has more columns than the header."}))
            else:
                rows.append(
                    (
                        line_number,
                        {
                            str(key).strip().lower(): (value or "").strip()
                            for key, value in row.items()
                            if key is not None
                        },
                    )
                )
            if len(rows) > MAX_IMPORT_ROWS:
                raise HTTPException(status_code=413, detail="CSV exceeds the 5,000-row limit.")
    except csv.Error as error:
        raise HTTPException(status_code=422, detail=f"Invalid CSV: {error}") from error
    if not rows:
        raise HTTPException(status_code=422, detail="CSV must include at least one data row.")
    return headers, rows


def _require_headers(headers: list[str], required: set[str]) -> None:
    missing = sorted(required - set(headers))
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"CSV is missing required columns: {', '.join(missing)}.",
        )


def _decimal(value: str, field: str, row_number: int, *, minimum: Decimal) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Row {row_number}: {field} must be a number.")
    if not parsed.is_finite() or parsed < minimum:
        raise ValueError(f"Row {row_number}: {field} must be at least {minimum}.")
    return parsed.quantize(MONEY, rounding=ROUND_HALF_UP)


def _integer(value: str, field: str, row_number: int, *, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Row {row_number}: {field} must be a whole number.")
    if parsed < minimum:
        raise ValueError(f"Row {row_number}: {field} must be at least {minimum}.")
    return parsed


def _validation_result(rows: list[dict[str, Any]], errors: list[str]) -> dict[str, Any]:
    return {
        "valid": not errors,
        "row_count": len(rows),
        "valid_count": len(rows) if not errors else 0,
        "errors": errors[:200],
        "truncated_errors": max(0, len(errors) - 200),
        "rows": rows[:100],
        "truncated_rows": max(0, len(rows) - 100),
    }


def _product_rows(
    csv_text: str,
    organization_id: int,
    db: Session,
) -> tuple[list[dict[str, Any]], list[str], int]:
    headers, source_rows = _parse_csv(csv_text)
    _require_headers(headers, {"sku", "name", "price"})
    existing_skus = {
        product.sku.casefold()
        for product in db.query(Product).filter(
            Product.organization_id == organization_id
        ).all()
    }
    seen_skus: set[str] = set()
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for line, row in source_rows:
        if "__error__" in row:
            errors.append(f"Row {line}: {row['__error__']}")
            continue
        try:
            sku = row.get("sku", "").strip()
            name = row.get("name", "").strip()
            if not sku or len(sku) > 100:
                raise ValueError(f"Row {line}: sku is required and must be at most 100 characters.")
            if not name or len(name) > 255:
                raise ValueError(f"Row {line}: name is required and must be at most 255 characters.")
            key = sku.casefold()
            if key in seen_skus:
                raise ValueError(f"Row {line}: duplicate SKU '{sku}' in this file.")
            if key in existing_skus:
                raise ValueError(f"Row {line}: SKU '{sku}' already exists.")
            price = _decimal(row.get("price", ""), "price", line, minimum=Decimal("0.01"))
            cost = (
                _decimal(row["cost"], "cost", line, minimum=Decimal("0"))
                if row.get("cost")
                else None
            )
            try:
                tax_rule_id = int(row["tax_rule_id"]) if row.get("tax_rule_id") else None
            except ValueError as error:
                raise ValueError(f"Row {line}: tax_rule_id must be a whole number.") from error
            if tax_rule_id is not None and not db.query(TaxRule).filter(
                TaxRule.id == tax_rule_id,
                TaxRule.organization_id == organization_id,
                TaxRule.is_active.is_(True),
            ).first():
                raise ValueError(f"Row {line}: active tax_rule_id '{tax_rule_id}' was not found.")
            normalized.append(
                {
                    "source_row": line,
                    "sku": sku,
                    "name": name,
                    "price": price,
                    "cost": cost,
                    "barcode": row.get("barcode") or None,
                    "category": row.get("category") or None,
                    "description": row.get("description") or None,
                    "tax_rule_id": tax_rule_id,
                }
            )
            seen_skus.add(key)
        except (ValueError, InvalidOperation) as error:
            errors.append(str(error))
    return normalized, errors, len(source_rows)


def _stock_rows(
    csv_text: str,
    organization_id: int,
    db: Session,
) -> tuple[list[dict[str, Any]], list[str], int]:
    headers, source_rows = _parse_csv(csv_text)
    _require_headers(headers, {"sku", "location_code", "quantity"})
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
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for line, row in source_rows:
        if "__error__" in row:
            errors.append(f"Row {line}: {row['__error__']}")
            continue
        sku = row.get("sku", "")
        location_code = row.get("location_code", "")
        try:
            if sku.casefold() not in products:
                raise ValueError(f"Row {line}: active product SKU '{sku}' was not found.")
            if location_code.casefold() not in locations:
                raise ValueError(f"Row {line}: active location code '{location_code}' was not found.")
            key = (sku.casefold(), location_code.casefold())
            if key in seen:
                raise ValueError(f"Row {line}: duplicate product/location pair.")
            quantity = _integer(row.get("quantity", ""), "quantity", line, minimum=0)
            normalized.append(
                {
                    "source_row": line,
                    "sku": sku,
                    "product_id": products[sku.casefold()].id,
                    "location_code": location_code,
                    "location_id": locations[location_code.casefold()].id,
                    "quantity": quantity,
                    "reason": "OPENING_BALANCE",
                }
            )
            seen.add(key)
        except ValueError as error:
            errors.append(str(error))
    return normalized, errors, len(source_rows)


def _historical_sale_rows(
    request: CSVImportRequest,
    organization_id: int,
    current_user: User,
    db: Session,
) -> tuple[list[dict[str, Any]], list[str], int]:
    headers, source_rows = _parse_csv(request.csv_text)
    _require_headers(
        headers,
        {
            "receipt_id",
            "sold_at",
            "sku",
            "quantity",
            "unit_price",
            "discount_per_item",
            "tax_rate",
            "tax_inclusive",
            "payment_method",
        },
    )
    if request.default_till_id is None:
        raise HTTPException(status_code=422, detail="Choose a default till for imported historical receipts.")
    till = db.query(Till).filter(
        Till.id == request.default_till_id,
        Till.organization_id == organization_id,
        Till.is_active.is_(True),
    ).first()
    if not till:
        raise HTTPException(status_code=422, detail="The selected default till is not active in this organization.")
    cashier_id = request.default_cashier_id or current_user.id
    cashier = db.query(User).filter(
        User.id == cashier_id,
        User.organization_id == organization_id,
        User.is_active.is_(True),
    ).first()
    if not cashier:
        raise HTTPException(status_code=422, detail="The selected default cashier is not active in this organization.")

    products = {
        product.sku.casefold(): product
        for product in db.query(Product).filter(
            Product.organization_id == organization_id,
            Product.is_active.is_(True),
        ).all()
    }
    references = {
        sale.external_reference
        for sale in db.query(Sale).filter(
            Sale.organization_id == organization_id,
            Sale.external_reference.is_not(None),
        ).all()
    }
    sales: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    seen_references: set[str] = set()
    for line, row in source_rows:
        if "__error__" in row:
            errors.append(f"Row {line}: {row['__error__']}")
            continue
        try:
            reference = row.get("receipt_id", "").strip()
            if not reference or len(reference) > 255:
                raise ValueError(f"Row {line}: receipt_id is required and must be at most 255 characters.")
            if reference in references:
                raise ValueError(f"Row {line}: receipt_id '{reference}' was already imported.")
            try:
                timestamp = datetime.fromisoformat(row.get("sold_at", "").replace("Z", "+00:00"))
            except ValueError as error:
                raise ValueError(f"Row {line}: sold_at must be an ISO 8601 timestamp.") from error
            if timestamp.tzinfo is None:
                raise ValueError(f"Row {line}: sold_at must include a timezone.")
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
            sku = row.get("sku", "")
            product = products.get(sku.casefold())
            if not product:
                raise ValueError(f"Row {line}: active product SKU '{sku}' was not found.")
            quantity = _integer(row.get("quantity", ""), "quantity", line, minimum=1)
            unit_price = _decimal(
                row.get("unit_price", ""),
                "unit_price",
                line,
                minimum=Decimal("0"),
            )
            discount_per_item = _decimal(
                row.get("discount_per_item", ""),
                "discount_per_item",
                line,
                minimum=Decimal("0"),
            )
            if discount_per_item > unit_price:
                raise ValueError(f"Row {line}: discount_per_item cannot exceed unit_price.")
            payment_method = row.get("payment_method", "").strip().upper()
            if not payment_method or len(payment_method) > 50:
                raise ValueError(f"Row {line}: payment_method is required and must be at most 50 characters.")
            tax_rate = _decimal(
                row.get("tax_rate", ""),
                "tax_rate",
                line,
                minimum=Decimal("0"),
            )
            if tax_rate > Decimal("100"):
                raise ValueError(f"Row {line}: tax_rate must not exceed 100.")
            tax_inclusive_raw = row.get("tax_inclusive", "").strip().casefold()
            if tax_inclusive_raw not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValueError(f"Row {line}: tax_inclusive must be true or false.")
            tax_inclusive = tax_inclusive_raw in {"true", "1", "yes"}
            group = sales.get(reference)
            if group is None:
                if reference in seen_references:
                    raise ValueError(f"Row {line}: receipt_id '{reference}' is duplicated inconsistently.")
                group = {
                    "reference": reference,
                    "source_row": line,
                    "created_at": timestamp,
                    "payment_method": payment_method,
                    "items": [],
                    "total": Decimal("0.00"),
                    "tax_total": Decimal("0.00"),
                    "discount_total": Decimal("0.00"),
                }
                sales[reference] = group
                seen_references.add(reference)
            elif group["created_at"] != timestamp or group["payment_method"] != payment_method:
                raise ValueError(f"Row {line}: receipt lines must share sold_at and payment_method.")

            gross_line = (unit_price * quantity).quantize(MONEY, rounding=ROUND_HALF_UP)
            discount_total = (discount_per_item * quantity).quantize(
                MONEY, rounding=ROUND_HALF_UP
            )
            base_total = gross_line - discount_total
            tax_amount = (
                (base_total * tax_rate / (Decimal("100") + tax_rate))
                if tax_inclusive and tax_rate
                else base_total * tax_rate / Decimal("100")
            ).quantize(MONEY, rounding=ROUND_HALF_UP)
            payable = base_total if tax_inclusive else base_total + tax_amount
            group["items"].append(
                {
                    "product_id": product.id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_per_item": discount_per_item,
                    "total_price": base_total,
                    "tax_rate": tax_rate,
                    "tax_inclusive": tax_inclusive,
                    "tax_amount": tax_amount,
                }
            )
            group["total"] += payable
            group["tax_total"] += tax_amount
            group["discount_total"] += discount_total
        except (ValueError, InvalidOperation) as error:
            errors.append(str(error))
    normalized = [
        {
            **sale,
            "till_id": till.id,
            "cashier_id": cashier.id,
            "location_id": till.location_id,
            "status": "COMPLETED",
        }
        for sale in sales.values()
    ]
    return normalized, errors, len(source_rows)


def _preview(
    import_type: str,
    request: CSVImportRequest,
    current_user: User,
    db: Session,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    if import_type == "products":
        rows, errors, count = _product_rows(request.csv_text, current_user.organization_id, db)
    elif import_type == "opening-inventory":
        rows, errors, count = _stock_rows(request.csv_text, current_user.organization_id, db)
    elif import_type == "historical-sales":
        rows, errors, count = _historical_sale_rows(
            request, current_user.organization_id, current_user, db
        )
    else:
        raise HTTPException(status_code=404, detail="Unknown setup import type.")
    preview_rows = [
        {
            "row": row.get("source_row", index + 2),
            "reference": row.get("sku", row.get("reference", "")),
            "status": "ready",
        }
        for index, row in enumerate(rows)
    ]
    return _validation_result(preview_rows, errors), rows, count


@router.post("/imports/{import_type}/preview")
def preview_setup_import(
    import_type: str,
    request: CSVImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    result, _, _ = _preview(import_type, request, current_user, db)
    return result


@router.post("/imports/{import_type}/commit")
def commit_setup_import(
    import_type: str,
    request: CSVImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    if len(request.csv_text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="CSV file exceeds the 5 MB limit.")
    content_hash = hashlib.sha256(request.csv_text.encode("utf-8")).hexdigest()
    existing_batch = db.query(DataImportBatch).filter(
        DataImportBatch.organization_id == current_user.organization_id,
        DataImportBatch.import_type == import_type,
        DataImportBatch.content_sha256 == content_hash,
    ).first()
    if existing_batch:
        return {
            "already_imported": True,
            "batch_id": existing_batch.id,
            "row_count": existing_batch.row_count,
        }

    preview, rows, row_count = _preview(import_type, request, current_user, db)
    if not preview["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "Import has validation errors.", "preview": preview},
        )

    batch = DataImportBatch(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        import_type=import_type,
        content_sha256=content_hash,
        row_count=row_count,
    )
    try:
        db.add(batch)
        db.flush()
        if import_type == "products":
            for row in rows:
                db.add(
                    Product(
                        organization_id=current_user.organization_id,
                        sku=row["sku"],
                        name=row["name"],
                        price=row["price"],
                        cost=row["cost"],
                        barcode=row["barcode"],
                        category=row["category"],
                        description=row["description"],
                        tax_rule_id=row["tax_rule_id"],
                        is_active=True,
                    )
                )
        elif import_type == "opening-inventory":
            pairs = [(row["product_id"], row["location_id"]) for row in rows]
            movement_totals = {
                (product_id, location_id): quantity
                for product_id, location_id, quantity in db.query(
                    InventoryMovement.product_id,
                    InventoryMovement.location_id,
                    func.coalesce(func.sum(InventoryMovement.quantity), 0),
                )
                .filter(
                    InventoryMovement.organization_id == current_user.organization_id,
                    tuple_(
                        InventoryMovement.product_id,
                        InventoryMovement.location_id,
                    ).in_(pairs),
                )
                .group_by(
                    InventoryMovement.product_id,
                    InventoryMovement.location_id,
                )
                .all()
            }
            for row in rows:
                current = movement_totals.get(
                    (row["product_id"], row["location_id"]), 0
                )
                delta = row["quantity"] - current
                if delta:
                    InventoryService.record_movement(
                        organization_id=current_user.organization_id,
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
                    current_user.organization_id,
                    row["product_id"],
                    row["location_id"],
                    db,
                    commit=False,
                )
        else:
            for row in rows:
                sale = Sale(
                    organization_id=current_user.organization_id,
                    till_id=row["till_id"],
                    cashier_id=row["cashier_id"],
                    total_amount=row["total"],
                    discount_amount=row["discount_total"],
                    tax_amount=row["tax_total"],
                    amount_tendered=row["total"],
                    change_given=Decimal("0.00"),
                    payment_method=row["payment_method"],
                    status="COMPLETED",
                    notes=f"Historical import; import batch {batch.id}.",
                    created_at=row["created_at"],
                    source_type="HISTORICAL_IMPORT",
                    external_reference=row["reference"],
                    fiscal_status="imported",
                )
                for item in row["items"]:
                    sale.sale_items.append(
                        SaleItem(
                            product_id=item["product_id"],
                            quantity=item["quantity"],
                            unit_price=item["unit_price"],
                            discount_per_item=item["discount_per_item"],
                            total_price=item["total_price"],
                            tax_rule_id=None,
                            tax_rate=item["tax_rate"],
                            tax_inclusive=item["tax_inclusive"],
                            tax_amount=item["tax_amount"],
                        )
                    )
                db.add(sale)
        db.commit()
        return {
            "already_imported": False,
            "batch_id": batch.id,
            "row_count": row_count,
            "record_count": len(rows),
        }
    except IntegrityError as error:
        db.rollback()
        existing_batch = db.query(DataImportBatch).filter(
            DataImportBatch.organization_id == current_user.organization_id,
            DataImportBatch.import_type == import_type,
            DataImportBatch.content_sha256 == content_hash,
        ).first()
        if existing_batch:
            return {
                "already_imported": True,
                "batch_id": existing_batch.id,
                "row_count": existing_batch.row_count,
            }
        raise HTTPException(
            status_code=409,
            detail="Import conflicts with existing data; no rows were committed.",
        ) from error
    except Exception:
        db.rollback()
        raise

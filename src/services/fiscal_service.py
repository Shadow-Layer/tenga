"""Independent, audited fiscal submission lifecycle."""

import json
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from src.models.entities import FiscalSubmission, Sale
from src.services.tengavfd_adapter import (
    FiscalConfigurationError,
    FiscalTransportError,
    create_tengavfd_adapter,
)


_STATUSES = {"PENDING", "SUBMITTED", "ACKNOWLEDGED", "FAILED", "UNCERTAIN"}
_RECONCILABLE = {"PENDING", "SUBMITTED", "UNCERTAIN"}


class FiscalService:
    @staticmethod
    def submit(
        sale: Sale,
        actor_id: int,
        db: Session,
        *,
        retry_failed: bool = False,
    ) -> FiscalSubmission:
        latest = db.query(FiscalSubmission).filter(
            FiscalSubmission.organization_id == sale.organization_id,
            FiscalSubmission.sale_id == sale.id,
        ).order_by(FiscalSubmission.attempt_number.desc()).first()
        if latest is not None and latest.status != "FAILED":
            return latest
        if latest is not None and not retry_failed:
            return latest
        if sale.status != "COMPLETED":
            raise ValueError("Only completed sales can be submitted for fiscalization")
        payload = FiscalService._build_payload(sale)
        attempt = FiscalSubmission(
            organization_id=sale.organization_id,
            sale_id=sale.id,
            attempt_number=(latest.attempt_number + 1) if latest else 1,
            status="PENDING",
            request_reference=f"TF-{secrets.token_urlsafe(24)}",
            request_payload=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        )
        db.add(attempt)
        sale.fiscal_submission_attempts = attempt.attempt_number
        sale.fiscal_status = "PENDING"
        sale.fiscal_status_updated_at = datetime.utcnow()
        db.commit()
        db.refresh(attempt)
        return FiscalService._submit_persisted(attempt, sale, db)

    @staticmethod
    def _submit_persisted(
        attempt: FiscalSubmission,
        sale: Sale,
        db: Session,
    ) -> FiscalSubmission:
        adapter = None
        try:
            adapter = create_tengavfd_adapter()
            result = adapter.submit(
                attempt.request_reference,
                json.loads(attempt.request_payload or "{}"),
            )
        except FiscalConfigurationError:
            FiscalService._set_status(
                attempt,
                sale,
                "FAILED",
                error="TengaVFD server-side configuration is incomplete",
                db=db,
            )
            return attempt
        except FiscalTransportError as exc:
            FiscalService._set_status(
                attempt,
                sale,
                "UNCERTAIN" if exc.uncertain else "FAILED",
                error=str(exc),
                db=db,
            )
            return attempt
        finally:
            if adapter is not None:
                adapter.close()
        return FiscalService._apply_remote_result(attempt, sale, result, db)

    @staticmethod
    def reconcile(
        attempt: FiscalSubmission,
        db: Session,
    ) -> FiscalSubmission:
        if attempt.status not in _RECONCILABLE:
            return attempt
        sale = db.query(Sale).filter(
            Sale.id == attempt.sale_id,
            Sale.organization_id == attempt.organization_id,
        ).first()
        if sale is None:
            raise ValueError("Sale not found for fiscal submission")
        adapter = create_tengavfd_adapter()
        try:
            result = adapter.status(attempt.request_reference)
        except FiscalConfigurationError:
            raise
        except FiscalTransportError as exc:
            attempt.status = "UNCERTAIN"
            attempt.error_message = str(exc)
            sale.fiscal_status = attempt.status
            sale.fiscal_status_updated_at = datetime.utcnow()
            db.commit()
            return attempt
        finally:
            adapter.close()
        return FiscalService._apply_remote_result(attempt, sale, result, db)

    @staticmethod
    def _apply_remote_result(
        attempt: FiscalSubmission,
        sale: Sale,
        result: Dict,
        db: Session,
    ) -> FiscalSubmission:
        status_value = str(result.get("status", "")).strip().upper()
        if status_value not in _STATUSES:
            status_value = "UNCERTAIN"
        fiscal_number = result.get("fiscal_number")
        if status_value == "ACKNOWLEDGED" and not fiscal_number:
            status_value = "UNCERTAIN"
        reference = result.get("request_reference")
        if reference and reference != attempt.request_reference:
            status_value = "UNCERTAIN"
        attempt.status = status_value
        attempt.error_message = None if status_value in {
            "PENDING", "SUBMITTED", "ACKNOWLEDGED"
        } else "Fiscal provider did not confirm a terminal result"
        attempt.response_payload = json.dumps({
            "status": status_value,
            "request_reference": attempt.request_reference,
            "fiscal_number": fiscal_number if status_value == "ACKNOWLEDGED" else None,
        }, sort_keys=True, separators=(",", ":"))
        if status_value in {"SUBMITTED", "ACKNOWLEDGED"} and attempt.submitted_at is None:
            attempt.submitted_at = datetime.utcnow()
        if status_value == "ACKNOWLEDGED":
            attempt.fiscal_number = str(fiscal_number)
            attempt.acknowledged_at = datetime.utcnow()
            sale.fiscal_number = str(fiscal_number)
        sale.fiscal_status = status_value
        sale.fiscal_status_updated_at = datetime.utcnow()
        db.commit()
        return attempt

    @staticmethod
    def _set_status(
        attempt: FiscalSubmission,
        sale: Sale,
        status: str,
        *,
        error: str,
        db: Session,
    ) -> None:
        attempt.status = status
        attempt.error_message = error
        sale.fiscal_status = status
        sale.fiscal_status_updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def _build_payload(sale: Sale) -> Dict:
        method = (sale.payment_method or "").upper()
        if method == "PAYNOW":
            method = "MOBILE_MONEY"
        lines = []
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        for item in sale.sale_items:
            lines.append({
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": str(Decimal(item.unit_price)),
                "total_price": str(Decimal(item.total_price)),
                "tax_rate": str(Decimal(item.tax_rate or 0)),
                "tax_amount": str(Decimal(item.tax_amount or 0)),
            })
            subtotal += Decimal(item.total_price)
            tax_total += Decimal(item.tax_amount or 0)
        return {
            "sale_id": str(sale.id),
            "currency": sale.currency_code,
            "timestamp": sale.created_at.isoformat(),
            "items": lines,
            "subtotal": str(subtotal),
            "tax_amount": str(tax_total),
            "total": str(Decimal(sale.total_amount)),
            "payment_method": method,
        }

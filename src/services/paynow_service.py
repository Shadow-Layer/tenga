"""Paynow initiation and server-verified payment settlement."""

import json
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.entities import PaymentAttempt, Sale
from src.services.paynow_adapter import (
    PaynowConfigurationError,
    PaynowTransportError,
    create_paynow_adapter,
)
from src.services.sale_service import SaleService


_PAID = {"PAID", "SUCCESS", "SUCCEEDED", "COMPLETED"}
_FAILED = {"FAILED", "CANCELLED", "CANCELED", "EXPIRED", "DECLINED"}
_PENDING = {"PENDING", "AWAITING", "PROCESSING", "INITIATED"}


class PaynowService:
    @staticmethod
    def initiate(attempt_id: int, phone_number: Optional[str], db: Session) -> PaymentAttempt:
        attempt = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id
        ).first()
        if attempt is None:
            raise ValueError("Payment attempt not found")
        if (
            attempt.status != "PENDING"
            or attempt.provider_reference
            or attempt.redirect_url
        ):
            return attempt
        adapter = None
        try:
            attempt.status = "INITIATING"
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
            adapter = create_paynow_adapter()
            provider_result = adapter.initiate({
                "merchant_reference": attempt.merchant_reference,
                "amount": str(Decimal(attempt.amount).quantize(Decimal("0.01"))),
                "currency": attempt.currency_code,
                "payment_method": attempt.payment_method,
                "phone_number": phone_number,
            })
            returned_reference = provider_result.get("merchant_reference")
            if returned_reference and returned_reference != attempt.merchant_reference:
                raise PaynowTransportError(
                    "Paynow initiation reference did not match", uncertain=True
                )
            attempt.provider_reference = (
                str(provider_result["provider_reference"])
                if provider_result.get("provider_reference") else None
            )
            redirect_url = provider_result.get("redirect_url")
            if redirect_url:
                parsed = urlparse(str(redirect_url))
                if parsed.scheme != "https" or not parsed.netloc:
                    raise PaynowTransportError(
                        "Paynow returned an invalid redirect URL", uncertain=True
                    )
                attempt.redirect_url = str(redirect_url)
            if not attempt.provider_reference and not attempt.redirect_url:
                attempt.status = "UNCERTAIN"
                attempt.failure_reason = "Paynow initiation response omitted payment references"
            else:
                attempt.status = "PENDING"
                attempt.failure_reason = None
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
        except PaynowConfigurationError:
            attempt.status = "FAILED"
            attempt.failure_reason = "Paynow server-side configuration is incomplete"
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
        except PaynowTransportError as exc:
            attempt.status = "UNCERTAIN" if exc.uncertain else "FAILED"
            attempt.failure_reason = str(exc)
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            if adapter is not None:
                adapter.close()
        return attempt

    @staticmethod
    def verify(attempt_id: int, db: Session) -> Tuple[PaymentAttempt, Sale]:
        attempt = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id
        ).first()
        if attempt is None:
            raise ValueError("Payment attempt not found")
        if attempt.status == "SETTLED":
            return attempt, attempt.sale
        adapter = create_paynow_adapter()
        try:
            result = adapter.verify(attempt.merchant_reference)
        except PaynowConfigurationError:
            raise
        except PaynowTransportError as exc:
            attempt.status = "UNCERTAIN"
            attempt.failure_reason = str(exc)
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
            return attempt, attempt.sale
        finally:
            adapter.close()

        if not PaynowService._matches_attempt(result, attempt):
            attempt.status = "FAILED"
            attempt.failure_reason = "Provider verification details did not match the attempt"
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
            return attempt, attempt.sale

        remote_status = str(result.get("status", "")).strip().upper()
        attempt.last_checked_at = datetime.utcnow()
        if remote_status in _PAID:
            provider_reference = str(result.get("provider_reference", "")).strip()
            if not provider_reference:
                attempt.status = "FAILED"
                attempt.failure_reason = "Verified provider result has no transaction reference"
                db.commit()
                return attempt, attempt.sale
            sale = SaleService.settle_paynow_attempt(
                attempt.id,
                provider_reference=provider_reference,
                db=db,
            )
            db.refresh(attempt)
            return attempt, sale
        if remote_status in _FAILED:
            attempt.status = "FAILED" if remote_status != "CANCELLED" else "CANCELLED"
            attempt.failure_reason = f"Provider reports {remote_status.lower()}"
        elif remote_status in _PENDING:
            attempt.status = "PENDING"
            attempt.failure_reason = None
        else:
            attempt.status = "UNCERTAIN"
            attempt.failure_reason = "Provider returned an unrecognized status"
        db.commit()
        return attempt, attempt.sale

    @staticmethod
    def _matches_attempt(result: Dict, attempt: PaymentAttempt) -> bool:
        try:
            amount = Decimal(str(result["amount"]))
            expected_amount = Decimal(attempt.amount).quantize(Decimal("0.01"))
        except (KeyError, ValueError, ArithmeticError):
            return False
        return (
            str(result.get("merchant_reference", "")) == attempt.merchant_reference
            and amount == expected_amount
            and str(result.get("currency", "")).strip().upper()
            == attempt.currency_code.strip().upper()
            and bool(str(result.get("status", "")).strip())
            and (
                attempt.provider_reference is None
                or not result.get("provider_reference")
                or str(result["provider_reference"]) == attempt.provider_reference
            )
        )

    @staticmethod
    def retry_failed(attempt_id: int, db: Session) -> Tuple[PaymentAttempt, bool]:
        source = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id
        ).first()
        if source is None:
            raise ValueError("Payment attempt not found")
        sale = db.query(Sale).filter(
            Sale.id == source.sale_id,
            Sale.organization_id == source.organization_id,
        ).with_for_update().first()
        if sale is None:
            raise ValueError("Sale not found")

        # Serialize retries for this sale, then re-read the source under lock.
        previous = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id,
            PaymentAttempt.sale_id == sale.id,
            PaymentAttempt.organization_id == sale.organization_id,
        ).with_for_update().first()
        if previous is None:
            raise ValueError("Payment attempt not found")

        existing = db.query(PaymentAttempt).filter(
            PaymentAttempt.retry_of_attempt_id == previous.id,
        ).first()
        if existing is not None:
            return existing, False

        newest = db.query(PaymentAttempt).filter(
            PaymentAttempt.sale_id == sale.id,
            PaymentAttempt.organization_id == sale.organization_id,
        ).order_by(PaymentAttempt.id.desc()).first()
        if newest is None or newest.id != previous.id:
            raise ValueError("Only the newest Paynow attempt can be retried")
        if previous.status != "FAILED":
            raise ValueError("Only a terminally failed Paynow attempt can be retried")
        if sale.status != "PENDING":
            raise ValueError("Only a pending sale can be retried")

        attempt = PaymentAttempt(
            organization_id=previous.organization_id,
            sale_id=previous.sale_id,
            retry_of_attempt_id=previous.id,
            till_session_id=previous.till_session_id,
            initiated_by_id=previous.initiated_by_id,
            provider="PAYNOW",
            payment_method=previous.payment_method,
            merchant_reference=f"TN-{secrets.token_urlsafe(24)}",
            amount=previous.amount,
            currency_code=previous.currency_code,
            status="PENDING",
        )
        db.add(attempt)
        try:
            db.commit()
        except IntegrityError:
            # The unique parent index is the final guard if concurrent callers
            # race on a database that does not honor SELECT FOR UPDATE.
            db.rollback()
            existing = db.query(PaymentAttempt).filter(
                PaymentAttempt.retry_of_attempt_id == previous.id,
            ).first()
            if existing is None:
                raise
            return existing, False
        return attempt, True

    @staticmethod
    def verify_callback_signature(
        raw_body: bytes,
        signature: str,
    ) -> bool:
        adapter = create_paynow_adapter()
        try:
            return adapter.verify_callback_signature(raw_body, signature)
        finally:
            adapter.close()

    @staticmethod
    def validate_callback_matches(callback: Dict, attempt: PaymentAttempt) -> bool:
        try:
            amount = Decimal(str(callback["amount"]))
        except (KeyError, ValueError, ArithmeticError):
            return False
        return (
            str(callback.get("merchant_reference", "")) == attempt.merchant_reference
            and amount == Decimal(attempt.amount).quantize(Decimal("0.01"))
            and str(callback.get("currency", "")).strip().upper()
            == attempt.currency_code.strip().upper()
            and (
                attempt.provider_reference is None
                or not callback.get("provider_reference")
                or str(callback["provider_reference"]) == attempt.provider_reference
            )
        )

    @staticmethod
    def callback_payload(raw_body: bytes) -> Dict:
        try:
            payload = json.loads(raw_body)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid callback payload") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid callback payload")
        return payload

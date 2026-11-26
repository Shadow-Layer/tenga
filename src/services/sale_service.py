"""POS transaction service for sale creation and processing.

Manages sale lifecycle (creation, queueing offline, committing).
Does NOT validate stock availability (decision U006).
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import secrets
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models.entities import (
    Sale,
    SaleItem,
    Product,
    Till,
    TillSession,
    User,
    Location,
    Organization,
    TaxRule,
    Payment,
    PaymentAttempt,
    ReceiptAudit,
)
from src.services.inventory_service import InventoryService
from src.services.till_service import TillService


class SaleService:
    """Manages POS sales and transaction lifecycle."""

    @staticmethod
    def create_sale(
        organization_id: int,
        till_id: int,
        cashier_id: int,
        payment_method: str,
        items: List[dict],
        amount_tendered: Optional[Decimal],
        till_session_id: Optional[int] = None,
        notes: Optional[str] = None,
        offline_device_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        expected_total: Optional[Decimal] = None,
        paynow_method: Optional[str] = None,
        paynow_phone_number: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Sale:
        """Create a sale (online or offline).

        Online cash sales and Paynow attempts require an open assigned session.
        Completed online cash sales require an idempotency key. Stock availability
        is deliberately not checked (decision U006).

        Args:
            organization_id: Organization ID
            till_id: Till ID
            cashier_id: User ID of cashier
            payment_method: CASH or PAYNOW
            items: List of dicts with keys: product_id, quantity, optional unit_price hint
            till_session_id: Required active till session ID
            notes: Optional notes
            offline_device_id: If provided, sale is created as PENDING (offline queued)
            db: Database session

        Returns:
            Created Sale

        Raises:
            ValueError: If entities don't exist or items invalid
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        # Validate entities
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        till = db.query(Till).filter(
            Till.id == till_id,
            Till.organization_id == organization_id,
        ).first()
        if not till:
            raise ValueError(f"Till {till_id} not found in org {organization_id}")
        TillService._lock_till_row(till_id, organization_id, db)
        db.refresh(till)

        cashier = db.query(User).filter(
            User.id == cashier_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
        ).first()
        if not cashier:
            raise ValueError(f"Cashier {cashier_id} not found in org {organization_id}")

        method = (payment_method or "").strip().upper()
        if paynow_method is not None:
            paynow_method = paynow_method.strip().upper()
        if method not in {"CASH", "PAYNOW"}:
            raise ValueError("Only CASH and PAYNOW payments are supported")
        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()
            if not 8 <= len(idempotency_key) <= 90:
                raise ValueError("Idempotency key must be between 8 and 90 characters")
        if method == "CASH" and not offline_device_id and not idempotency_key:
            raise ValueError("An idempotency key is required for cash sales")
        if method == "PAYNOW":
            if offline_device_id:
                raise ValueError("Paynow payments cannot be queued as offline sales")
            if paynow_method not in {"HOSTED", "MOBILE_MONEY"}:
                raise ValueError("Paynow method must be HOSTED or MOBILE_MONEY")
            if paynow_method == "MOBILE_MONEY" and not (paynow_phone_number or "").strip():
                raise ValueError("A phone number is required for mobile-money push")
            if not idempotency_key or not idempotency_key.strip():
                raise ValueError("An idempotency key is required for Paynow")
        elif paynow_method is not None or paynow_phone_number is not None:
            raise ValueError("Paynow options are only valid for Paynow payments")

        external_reference = (
            f"POS:{idempotency_key.strip()}" if idempotency_key else None
        )
        if external_reference:
            existing_sale = db.query(Sale).filter(
                Sale.organization_id == organization_id,
                Sale.external_reference == external_reference,
            ).first()
            if existing_sale is not None:
                SaleService._assert_idempotent_replay(
                    existing_sale,
                    till_id=till_id,
                    till_session_id=till_session_id,
                    cashier_id=cashier_id,
                    payment_method=method,
                    paynow_method=paynow_method,
                    items=items,
                    amount_tendered=amount_tendered,
                    expected_total=expected_total,
                    db=db,
                )
                return existing_sale

        # A sale is always attached to the authenticated operator's active session.
        if till_session_id is None:
            raise ValueError("An open till session is required")
        till_session = db.query(TillSession).filter(
            TillSession.id == till_session_id,
            TillSession.organization_id == organization_id,
            TillSession.till_id == till_id,
        ).first()
        if till_session is None:
            raise ValueError("Till session not found for this organization and till")
        if (till_session.status or "").upper() != "OPEN":
            raise ValueError("Till session is not open")
        if till_session.operator_id != cashier_id:
            raise ValueError("Till session belongs to a different operator")
        if not till.is_active:
            raise ValueError("Till is inactive")
        location = db.query(Location).filter(
            Location.id == till.location_id,
            Location.organization_id == organization_id,
            Location.is_active.is_(True),
        ).first()
        if location is None:
            raise ValueError("Till location is not active in this organization")
        currency = (org.currency_code or "").strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("A valid organization currency must be configured")
        if (till_session.currency_code or "").strip().upper() != currency:
            raise ValueError("Till session currency does not match the organization")
        try:
            TillService.require_assigned_user(till, cashier, db)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        # Validate items
        if not items:
            raise ValueError("Sale must have at least one item")

        total_amount = Decimal("0.00")
        discount_amount = Decimal("0.00")
        tax_amount = Decimal("0.00")
        money = Decimal("0.01")

        # Create sale
        sale = Sale(
            organization_id=organization_id,
            till_id=till_id,
            cashier_id=cashier_id,
            total_amount=0,  # Will be set after items
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            amount_tendered=Decimal(amount_tendered or 0),
            change_given=Decimal("0.00"),
            payment_method=method,
            status="PENDING" if offline_device_id or method == "PAYNOW" else "COMPLETED",
            notes=notes,
            created_at=datetime.utcnow(),
            till_session_id=till_session.id,
            location_id=location.id,
            currency_code=currency,
            external_reference=external_reference,
            fiscal_status="PENDING",
        )

        # Process items
        for item_data in items:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 0)
            client_price = item_data.get("unit_price")

            if not product_id or quantity <= 0:
                raise ValueError(
                    f"Invalid item: product_id={product_id}, quantity={quantity}, unit_price={client_price}"
                )

            # Validate product exists
            product = db.query(Product).filter(
                Product.id == product_id,
                Product.organization_id == organization_id,
            ).first()
            if not product:
                raise ValueError(
                    f"Product {product_id} not found in org {organization_id}"
                )

            unit_price = Decimal(product.price).quantize(money)
            if client_price is not None and Decimal(client_price).quantize(money) != unit_price:
                raise ValueError("Confirmed unit-price snapshot no longer matches the product price")
            item_total = (unit_price * quantity).quantize(
                money, rounding=ROUND_HALF_UP
            )
            rule = None
            if product.tax_rule_id is not None:
                rule = db.query(TaxRule).filter(
                    TaxRule.id == product.tax_rule_id,
                    TaxRule.organization_id == organization_id,
                ).first()
                if not rule or not rule.is_active:
                    raise ValueError(
                        f"Product {product_id} has no active assigned tax rule"
                    )

            rate = Decimal(rule.rate) if rule else Decimal("0")
            tax_inclusive = bool(rule.tax_inclusive) if rule else False
            client_tax_rate = item_data.get("tax_rate")
            client_tax_inclusive = item_data.get("tax_inclusive")
            if (client_tax_rate is None) != (client_tax_inclusive is None):
                raise ValueError("Both tax-rate and tax-inclusive snapshots are required")
            if client_tax_rate is not None and (
                Decimal(client_tax_rate) != rate
                or bool(client_tax_inclusive) != tax_inclusive
            ):
                raise ValueError("Confirmed tax snapshot no longer matches the product tax rule")
            if rate and tax_inclusive:
                line_tax = (
                    item_total * rate / (Decimal("100") + rate)
                ).quantize(money, rounding=ROUND_HALF_UP)
                line_payable = item_total
            elif rate:
                line_tax = (
                    item_total * rate / Decimal("100")
                ).quantize(money, rounding=ROUND_HALF_UP)
                line_payable = item_total + line_tax
            else:
                line_tax = Decimal("0.00")
                line_payable = item_total

            total_amount += line_payable
            tax_amount += line_tax

            sale_item = SaleItem(
                sale=sale,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount_per_item=Decimal("0.00"),
                total_price=item_total,
                tax_rule_id=rule.id if rule else None,
                tax_rate=rate,
                tax_inclusive=tax_inclusive,
                tax_amount=line_tax,
            )

        sale.total_amount = total_amount
        sale.tax_amount = tax_amount
        if expected_total is not None and Decimal(expected_total).quantize(money) != total_amount:
            raise ValueError("Confirmed checkout total no longer matches current product and tax prices")
        if method == "CASH":
            if amount_tendered is None:
                raise ValueError("Cash tendered is required for cash sales")
            tendered = Decimal(amount_tendered).quantize(money)
            if tendered < total_amount:
                raise ValueError("Cash tendered is less than the sale total")
            sale.amount_tendered = tendered
            sale.change_given = (tendered - total_amount).quantize(money)
        else:
            sale.amount_tendered = Decimal("0.00")
            sale.change_given = Decimal("0.00")
        db.add(sale)
        db.flush()

        # For online sales (not offline), generate movements immediately
        if method == "CASH" and not offline_device_id:
            SaleService._generate_movements_for_sale(sale, cashier_id, db)
            db.add(Payment(
                organization_id=organization_id,
                sale_id=sale.id,
                payment_method="CASH",
                amount=total_amount,
                amount_tendered=sale.amount_tendered,
                change_given=sale.change_given,
                currency_code=currency,
                status="COMPLETED",
            ))
            db.add(ReceiptAudit(
                organization_id=organization_id,
                sale_id=sale.id,
                actor_id=cashier_id,
                action="ISSUED",
            ))
        elif method == "PAYNOW":
            merchant_reference = PaymentAttempt.__table__.c.merchant_reference.type.length
            if len(idempotency_key.strip()) > merchant_reference - 8:
                raise ValueError("Idempotency key is too long")
            db.add(PaymentAttempt(
                organization_id=organization_id,
                sale_id=sale.id,
                till_session_id=till_session.id,
                initiated_by_id=cashier_id,
                provider="PAYNOW",
                payment_method=paynow_method,
                merchant_reference=f"TN-{secrets.token_urlsafe(24)}",
                amount=total_amount,
                currency_code=currency,
                status="PENDING",
            ))

        try:
            db.commit()
        except Exception:
            db.rollback()
            if external_reference:
                existing_sale = db.query(Sale).filter(
                    Sale.organization_id == organization_id,
                    Sale.external_reference == external_reference,
                ).first()
                if existing_sale is not None:
                    SaleService._assert_idempotent_replay(
                        existing_sale,
                        till_id=till_id,
                        till_session_id=till_session_id,
                        cashier_id=cashier_id,
                        payment_method=method,
                        paynow_method=paynow_method,
                        items=items,
                        amount_tendered=amount_tendered,
                        expected_total=expected_total,
                        db=db,
                    )
                    return existing_sale
            raise
        return sale

    @staticmethod
    def _assert_idempotent_replay(
        sale: Sale,
        *,
        till_id: int,
        till_session_id: int,
        cashier_id: int,
        payment_method: str,
        paynow_method: Optional[str],
        items: List[dict],
        amount_tendered: Optional[Decimal],
        expected_total: Optional[Decimal],
        db: Session,
    ) -> None:
        requested = sorted(
            (int(item["product_id"]), int(item["quantity"])) for item in items
        )
        existing = sorted(
            (item.product_id, item.quantity) for item in sale.sale_items
        )
        snapshots_match = True
        has_line_snapshots = any(
            item.get("unit_price") is not None
            or item.get("tax_rate") is not None
            or item.get("tax_inclusive") is not None
            for item in items
        )
        if has_line_snapshots:
            if expected_total is not None and any(
                item.get("unit_price") is None
                or item.get("tax_rate") is None
                or item.get("tax_inclusive") is None
                for item in items
            ):
                snapshots_match = False
            else:
                requested_items = sorted(
                    items,
                    key=lambda item: (int(item["product_id"]), int(item["quantity"])),
                )
                existing_items = sorted(
                    sale.sale_items,
                    key=lambda item: (item.product_id, item.quantity),
                )
                snapshots_match = len(requested_items) == len(existing_items) and all(
                    (
                        request_item.get("unit_price") is None
                        or Decimal(request_item["unit_price"]).quantize(Decimal("0.01"))
                        == Decimal(sale_item.unit_price).quantize(Decimal("0.01"))
                    )
                    and (
                        request_item.get("tax_rate") is None
                        or Decimal(request_item["tax_rate"]) == Decimal(sale_item.tax_rate)
                    )
                    and (
                        request_item.get("tax_inclusive") is None
                        or bool(request_item["tax_inclusive"]) == bool(sale_item.tax_inclusive)
                    )
                    for request_item, sale_item in zip(requested_items, existing_items)
                )
        if (
            sale.till_id != till_id
            or sale.till_session_id != till_session_id
            or sale.cashier_id != cashier_id
            or sale.payment_method.upper() != payment_method
            or requested != existing
            or not snapshots_match
            or (
                expected_total is not None
                and Decimal(sale.total_amount).quantize(Decimal("0.01"))
                != Decimal(expected_total).quantize(Decimal("0.01"))
            )
            or (
                payment_method == "PAYNOW"
                and db.query(PaymentAttempt).filter(
                    PaymentAttempt.sale_id == sale.id,
                    PaymentAttempt.payment_method == paynow_method,
                ).first() is None
            )
            or (
                payment_method == "CASH"
                and Decimal(sale.amount_tendered)
                != Decimal(amount_tendered or 0).quantize(Decimal("0.01"))
            )
        ):
            raise ValueError("Idempotency key was already used with a different sale")

    @staticmethod
    def settle_paynow_attempt(
        attempt_id: int,
        *,
        provider_reference: str,
        db: Session,
    ) -> Sale:
        """Settle a Paynow attempt only after the caller has verified provider status."""
        attempt = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id
        ).first()
        if attempt is None:
            raise ValueError("Payment attempt not found")
        if attempt.provider != "PAYNOW":
            raise ValueError("Payment attempt provider is not Paynow")
        till_session = db.query(TillSession).filter(
            TillSession.id == attempt.till_session_id,
            TillSession.organization_id == attempt.organization_id,
        ).first()
        if till_session is None:
            raise ValueError("Payment attempt has no valid till session")
        TillService._lock_till_row(
            till_session.till_id,
            attempt.organization_id,
            db,
        )
        attempt = db.query(PaymentAttempt).filter(
            PaymentAttempt.id == attempt_id
        ).with_for_update().first()
        if attempt.status == "SETTLED":
            return attempt.sale
        if attempt.status not in {"PENDING", "UNCERTAIN", "FAILED"}:
            raise ValueError(f"Payment attempt cannot settle from {attempt.status}")
        sale = db.query(Sale).filter(
            Sale.id == attempt.sale_id,
            Sale.organization_id == attempt.organization_id,
        ).with_for_update().first()
        if sale is None:
            raise ValueError("Sale not found for payment attempt")
        if sale.status == "COMPLETED":
            attempt.status = "FAILED"
            attempt.failure_reason = "Sale has already been settled by another payment attempt"
            attempt.last_checked_at = datetime.utcnow()
            db.commit()
            return sale
        if sale.status != "PENDING" or not sale.till_session_id:
            raise ValueError("Sale is not pending Paynow settlement")
        if (
            sale.till_session_id != attempt.till_session_id
            or sale.payment_method.upper() != "PAYNOW"
            or Decimal(sale.total_amount) != Decimal(attempt.amount)
            or (sale.currency_code or "").upper() != attempt.currency_code.upper()
            or (till_session.currency_code or "").upper() != attempt.currency_code.upper()
        ):
            raise ValueError("Payment attempt is not linked to the sale session")
        sale.status = "COMPLETED"
        sale.amount_tendered = attempt.amount
        sale.change_given = Decimal("0.00")
        sale.updated_at = datetime.utcnow()
        attempt.status = "SETTLED"
        attempt.provider_reference = provider_reference
        attempt.verified_at = datetime.utcnow()
        attempt.last_checked_at = attempt.verified_at
        db.add(Payment(
            organization_id=sale.organization_id,
            sale_id=sale.id,
            payment_method="PAYNOW",
            amount=attempt.amount,
            amount_tendered=attempt.amount,
            change_given=Decimal("0.00"),
            currency_code=attempt.currency_code,
            status="COMPLETED",
            provider_reference=provider_reference,
        ))
        SaleService._generate_movements_for_sale(sale, sale.cashier_id, db)
        db.add(ReceiptAudit(
            organization_id=sale.organization_id,
            sale_id=sale.id,
            actor_id=attempt.initiated_by_id,
            action="ISSUED",
        ))
        db.commit()
        return sale

    @staticmethod
    def commit_pending_sale(
        sale_id: int,
        recorded_by_id: int,
        db: Session,
        commit: bool = True,
    ) -> None:
        """Commit a pending (offline-queued) sale and generate inventory movements.

        This is called during sync to apply queued sales to the server.
        Idempotent: calling multiple times on the same sale generates movements only once.

        Args:
            sale_id: Sale ID to commit
            recorded_by_id: User ID performing commit (for audit)
            db: Database session

        Raises:
            ValueError: If sale not found or already committed
        """
        sale = (
            db.query(Sale)
            .filter(Sale.id == sale_id)
            .with_for_update()
            .first()
        )
        if not sale:
            raise ValueError(f"Sale {sale_id} not found")
        TillService._lock_till_row(sale.till_id, sale.organization_id, db)
        sale = db.query(Sale).filter(
            Sale.id == sale_id
        ).with_for_update().first()
        if not sale:
            raise ValueError(f"Sale {sale_id} not found")

        # Already committed
        if sale.status == "COMPLETED":
            return

        if sale.status != "PENDING":
            raise ValueError(f"Sale {sale_id} cannot be committed from status {sale.status}")
        if (sale.payment_method or "").upper() != "CASH":
            raise ValueError("Unverified non-cash payments cannot be committed by offline sync")

        if sale.till_session_id is None:
            raise ValueError("Pending sale is not linked to a till session")
        till_session = db.query(TillSession).filter(
            TillSession.id == sale.till_session_id,
            TillSession.organization_id == sale.organization_id,
            TillSession.till_id == sale.till_id,
        ).first()
        if till_session is None or (till_session.status or "").upper() != "OPEN":
            raise ValueError("Pending sale requires its original open till session")
        if (
            till_session.operator_id != recorded_by_id
            or sale.cashier_id != recorded_by_id
        ):
            raise ValueError("Pending sale session belongs to a different operator")
        cashier = db.query(User).filter(
            User.id == recorded_by_id,
            User.organization_id == sale.organization_id,
            User.is_active.is_(True),
        ).first()
        till = db.query(Till).filter(
            Till.id == sale.till_id,
            Till.organization_id == sale.organization_id,
        ).first()
        if cashier is None or till is None:
            raise ValueError("Pending sale operator or till is not available")
        if (
            sale.location_id != till.location_id
            or (sale.currency_code or "").upper()
            != (till_session.currency_code or "").upper()
        ):
            raise ValueError("Pending sale location or currency does not match its session")
        TillService.require_assigned_user(till, cashier, db)

        # Generate inventory movements and sale state in one database transaction.
        SaleService._generate_movements_for_sale(sale, recorded_by_id, db)

        if db.query(Payment.id).filter(
            Payment.organization_id == sale.organization_id,
            Payment.sale_id == sale.id,
        ).first() is None:
            db.add(Payment(
                organization_id=sale.organization_id,
                sale_id=sale.id,
                payment_method="CASH",
                amount=sale.total_amount,
                amount_tendered=sale.amount_tendered,
                change_given=sale.change_given,
                currency_code=sale.currency_code,
                status="COMPLETED",
            ))
        if db.query(ReceiptAudit.id).filter(
            ReceiptAudit.organization_id == sale.organization_id,
            ReceiptAudit.sale_id == sale.id,
            ReceiptAudit.action == "ISSUED",
        ).first() is None:
            db.add(ReceiptAudit(
                organization_id=sale.organization_id,
                sale_id=sale.id,
                actor_id=recorded_by_id,
                action="ISSUED",
            ))

        # Mark sale as committed
        sale.status = "COMPLETED"
        sale.updated_at = datetime.utcnow()
        db.flush()
        if commit:
            db.commit()

    @staticmethod
    def get_pending_sales(
        organization_id: int,
        db: Session,
    ) -> List[Sale]:
        """Fetch all pending sales awaiting commitment.

        Args:
            organization_id: Organization ID
            db: Database session

        Returns:
            List of PENDING sales
        """
        return db.query(Sale).filter(
            Sale.organization_id == organization_id,
            Sale.status == "PENDING",
        ).order_by(Sale.created_at).all()

    @staticmethod
    def _generate_movements_for_sale(
        sale: "Sale",
        recorded_by_id: int,
        db: Session,
    ) -> None:
        """Generate inventory movements for a sale (helper for commit and online creation).
        
        Idempotent: only creates movements if they don't already exist.
        """
        from src.models.entities import InventoryMovement
        
        quantities_by_product: dict[int, int] = {}
        for sale_item in sale.sale_items:
            quantities_by_product[sale_item.product_id] = (
                quantities_by_product.get(sale_item.product_id, 0)
                + sale_item.quantity
            )

        for product_id, quantity in quantities_by_product.items():
            # Check if movement already exists (idempotency)
            existing = db.query(InventoryMovement).filter(
                InventoryMovement.reference_type == "SALE",
                InventoryMovement.reference_id == sale.id,
                InventoryMovement.product_id == product_id,
            ).first()

            if existing:
                continue  # Skip if already created

            # Record negative movement (stock out)
            InventoryService.record_movement(
                organization_id=sale.organization_id,
                product_id=product_id,
                location_id=sale.till.location_id,
                quantity=-quantity,
                reason="SALE",
                recorded_by_id=recorded_by_id,
                reference_type="SALE",
                reference_id=sale.id,
                db=db,
                commit=False,
            )

            # Update stock cache
            InventoryService.update_stock_cache(
                organization_id=sale.organization_id,
                product_id=product_id,
                location_id=sale.till.location_id,
                db=db,
                commit=False,
            )

    @staticmethod
    def get_sale(
        sale_id: int,
        db: Session,
    ) -> Optional[Sale]:
        """Fetch a sale by ID.

        Args:
            sale_id: Sale ID
            db: Database session

        Returns:
            Sale or None
        """
        return db.query(Sale).filter(Sale.id == sale_id).first()

    @staticmethod
    def get_sales_in_session(
        till_session_id: int,
        db: Session,
    ) -> List[Sale]:
        """Fetch all sales in a till session.

        Args:
            till_session_id: Till session ID
            db: Database session

        Returns:
            List of sales
        """
        return db.query(Sale).filter(
            Sale.till_session_id == till_session_id
        ).order_by(Sale.created_at).all()

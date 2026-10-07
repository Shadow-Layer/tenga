"""POS transaction service for sale creation and processing.

Manages sale lifecycle (creation, queueing offline, committing).
Does NOT validate stock availability (decision U006).
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.models.entities import (
    Sale,
    SaleItem,
    Product,
    Till,
    User,
    Location,
    Organization,
)
from src.services.inventory_service import InventoryService


class SaleService:
    """Manages POS sales and transaction lifecycle."""

    @staticmethod
    def create_sale(
        organization_id: int,
        till_id: int,
        cashier_id: int,
        payment_method: str,
        items: List[dict],
        till_session_id: Optional[int] = None,
        notes: Optional[str] = None,
        offline_device_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Sale:
        """Create a sale (online or offline).

        Sale is created with PENDING status if offline, COMPLETED if online.
        Note: Stock availability is NOT checked (decision U006).

        Args:
            organization_id: Organization ID
            till_id: Till ID
            cashier_id: User ID of cashier
            payment_method: Payment method (CASH, CARD, MOBILE, etc.)
            items: List of dicts with keys: product_id, quantity, unit_price
            till_session_id: Optional till session ID
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

        cashier = db.query(User).filter(
            User.id == cashier_id,
            User.organization_id == organization_id,
        ).first()
        if not cashier:
            raise ValueError(f"Cashier {cashier_id} not found in org {organization_id}")

        # Validate items
        if not items:
            raise ValueError("Sale must have at least one item")

        total_amount = 0
        discount_amount = 0
        tax_amount = 0

        # Create sale
        sale = Sale(
            organization_id=organization_id,
            till_id=till_id,
            cashier_id=cashier_id,
            total_amount=0,  # Will be set after items
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            payment_method=payment_method,
            status="PENDING" if offline_device_id else "COMPLETED",
            notes=notes,
            created_at=datetime.utcnow(),
        )

        # Process items
        for item_data in items:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 0)
            unit_price = item_data.get("unit_price")

            if not product_id or quantity <= 0 or unit_price is None:
                raise ValueError(
                    f"Invalid item: product_id={product_id}, quantity={quantity}, unit_price={unit_price}"
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

            item_total = quantity * float(unit_price)
            total_amount += item_total

            sale_item = SaleItem(
                sale=sale,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                discount_per_item=item_data.get("discount_per_item", 0),
                total_price=item_total,
            )
            sale.sale_items.append(sale_item)

        sale.total_amount = total_amount
        db.add(sale)
        db.commit()

        return sale

    @staticmethod
    def commit_pending_sale(
        sale_id: int,
        recorded_by_id: int,
        db: Session,
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
        sale = db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError(f"Sale {sale_id} not found")

        # Already committed
        if sale.status == "COMPLETED":
            return

        # Generate inventory movements for each item (one movement per product)
        for sale_item in sale.sale_items:
            # Check if movement already exists (idempotency)
            from src.models.entities import InventoryMovement
            existing = db.query(InventoryMovement).filter(
                InventoryMovement.reference_type == "SALE",
                InventoryMovement.reference_id == sale.id,
                InventoryMovement.product_id == sale_item.product_id,
            ).first()

            if existing:
                continue  # Skip if already created

            # Record negative movement (stock out)
            InventoryService.record_movement(
                organization_id=sale.organization_id,
                product_id=sale_item.product_id,
                location_id=sale.till.location_id,
                quantity=-sale_item.quantity,  # Negative for sale
                reason="SALE",
                recorded_by_id=recorded_by_id,
                reference_type="SALE",
                reference_id=sale.id,
                db=db,
            )

            # Update stock cache
            InventoryService.update_stock_cache(
                organization_id=sale.organization_id,
                product_id=sale_item.product_id,
                location_id=sale.till.location_id,
                db=db,
            )

        # Mark sale as committed
        sale.status = "COMPLETED"
        sale.updated_at = datetime.utcnow()
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

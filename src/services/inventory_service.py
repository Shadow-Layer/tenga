"""Inventory movement ledger and reconciliation service.

Manages append-only inventory movements and detects discrepancies from
offline overselling (decision U006).
"""
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models.entities import (
    InventoryMovement,
    Product,
    Location,
    Stock,
    Organization,
)


class InventoryService:
    """Manages inventory movements and reconciliation."""

    @staticmethod
    def record_movement(
        organization_id: int,
        product_id: int,
        location_id: int,
        quantity: int,
        reason: str,
        recorded_by_id: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> InventoryMovement:
        """Record an inventory movement (immutable append).

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            quantity: Signed quantity (negative for sale/out, positive for in)
            reason: Reason for movement (SALE, PURCHASE, ADJUSTMENT, etc.)
            recorded_by_id: User ID who recorded movement
            reference_type: Type of reference (SALE, PO, etc.)
            reference_id: ID of reference (sale_id, po_id, etc.)
            db: Database session

        Returns:
            Created InventoryMovement

        Raises:
            ValueError: If required entities don't exist
        """
        if db is None:
            from src.database import get_db
            db = next(get_db())

        # Validate entities exist
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        product = db.query(Product).filter(
            Product.id == product_id,
            Product.organization_id == organization_id,
        ).first()
        if not product:
            raise ValueError(f"Product {product_id} not found in org {organization_id}")

        location = db.query(Location).filter(
            Location.id == location_id,
            Location.organization_id == organization_id,
        ).first()
        if not location:
            raise ValueError(f"Location {location_id} not found in org {organization_id}")

        movement = InventoryMovement(
            organization_id=organization_id,
            product_id=product_id,
            location_id=location_id,
            movement_type="OUT" if quantity < 0 else "IN",
            quantity=quantity,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            recorded_by_id=recorded_by_id,
            created_at=datetime.utcnow(),
        )
        db.add(movement)
        db.commit()
        return movement

    @staticmethod
    def compute_stock_at_location(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
        as_of: Optional[datetime] = None,
    ) -> int:
        """Compute current stock by summing all movements for a product at location.

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            db: Database session
            as_of: Optional datetime to compute stock as of that time

        Returns:
            Net quantity at location
        """
        query = db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
            InventoryMovement.location_id == location_id,
        )

        if as_of:
            query = query.filter(InventoryMovement.created_at <= as_of)

        movements = query.all()
        total = sum(m.quantity for m in movements)
        return total

    @staticmethod
    def detect_discrepancy(
        organization_id: int,
        product_id: int,
        location_id: int,
        expected_quantity: int,
        db: Session,
    ) -> Optional[int]:
        """Detect if physical count reveals a discrepancy from ledger.

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            expected_quantity: Expected quantity from physical count
            db: Database session

        Returns:
            Discrepancy amount (positive = surplus, negative = shortage), or None if match
        """
        ledger_qty = InventoryService.compute_stock_at_location(
            organization_id,
            product_id,
            location_id,
            db,
        )

        discrepancy = expected_quantity - ledger_qty
        return discrepancy if discrepancy != 0 else None

    @staticmethod
    def record_reconciliation(
        organization_id: int,
        product_id: int,
        location_id: int,
        expected_quantity: int,
        recorded_by_id: int,
        reason: str,
        db: Session,
    ) -> Tuple[InventoryMovement, Optional[int]]:
        """Record a physical count and detect/reconcile discrepancy.

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            expected_quantity: Expected quantity from physical count
            recorded_by_id: User ID who performed count
            reason: Reason for count (RECONCILIATION, CYCLE_COUNT, etc.)
            db: Database session

        Returns:
            Tuple of (movement_record, discrepancy_amount or None)

        Raises:
            ValueError: If entities don't exist
        """
        discrepancy = InventoryService.detect_discrepancy(
            organization_id,
            product_id,
            location_id,
            expected_quantity,
            db,
        )

        # Record COUNT movement to capture the expected quantity at this point
        movement = InventoryService.record_movement(
            organization_id,
            product_id,
            location_id,
            quantity=0,  # COUNT doesn't change stock; it's just a snapshot
            reason=reason,
            recorded_by_id=recorded_by_id,
            reference_type="COUNT",
            reference_id=None,
            db=db,
        )

        return movement, discrepancy

    @staticmethod
    def get_movements_for_product_at_location(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
        limit: int = 100,
    ) -> List[InventoryMovement]:
        """Fetch recent movements for a product at a location (for audit trail).

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            db: Database session
            limit: Maximum records to return

        Returns:
            List of InventoryMovement records, newest first
        """
        return db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product_id,
            InventoryMovement.location_id == location_id,
        ).order_by(desc(InventoryMovement.created_at)).limit(limit).all()

    @staticmethod
    def get_stock_snapshot(
        organization_id: int,
        location_id: int,
        db: Session,
    ) -> List[Tuple[int, int]]:
        """Get current stock for all products at a location.

        Args:
            organization_id: Organization ID
            location_id: Location ID
            db: Database session

        Returns:
            List of (product_id, quantity) tuples
        """
        stock_records = db.query(Stock).filter(
            Stock.organization_id == organization_id,
            Stock.location_id == location_id,
        ).all()

        return [(s.product_id, s.quantity) for s in stock_records]

    @staticmethod
    def update_stock_cache(
        organization_id: int,
        product_id: int,
        location_id: int,
        db: Session,
    ) -> None:
        """Update Stock table (cache) for a product at location.

        This is called after movements are applied to keep Stock table in sync.

        Args:
            organization_id: Organization ID
            product_id: Product ID
            location_id: Location ID
            db: Database session
        """
        quantity = InventoryService.compute_stock_at_location(
            organization_id,
            product_id,
            location_id,
            db,
        )

        stock = db.query(Stock).filter(
            Stock.organization_id == organization_id,
            Stock.product_id == product_id,
            Stock.location_id == location_id,
        ).first()

        if stock:
            stock.quantity = quantity
            stock.last_movement_at = datetime.utcnow()
        else:
            stock = Stock(
                organization_id=organization_id,
                product_id=product_id,
                location_id=location_id,
                quantity=quantity,
                last_movement_at=datetime.utcnow(),
            )
            db.add(stock)

        db.commit()

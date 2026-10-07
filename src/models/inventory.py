"""Inventory movement ledger and conflict reconciliation models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Float, Index, ForeignKey,
    CheckConstraint, UniqueConstraint, event, and_
)
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import IntegrityError

from src.database import Base


class MovementType(str, Enum):
    """Types of inventory movements."""
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
    COUNT = "COUNT"


class DiscrepancyStatus(str, Enum):
    """Status of inventory discrepancy."""
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    WAIVED = "WAIVED"


class InventoryMovement(Base):
    """
    Immutable append-only ledger of all inventory movements.
    
    Each movement represents a change to stock at a location.
    Movement types:
    - SALE: Stock out of a location (no to_location_id)
    - ADJUSTMENT: Manual inventory adjustment (positive or negative)
    - TRANSFER: Stock move from one location to another
    - COUNT: Physical count reconciliation
    
    CRITICAL: This table is immutable. No UPDATE or DELETE operations are permitted
    after creation. Attempts to modify will fail at DB level.
    """
    __tablename__ = "inventory_movements"

    id = Column(String(36), primary_key=True)
    
    # Movement metadata
    type = Column(String(20), nullable=False)  # SALE, ADJUSTMENT, TRANSFER, COUNT
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Quantity: positive=in, negative=out
    # For SALE: always negative (stock decreases)
    # For ADJUSTMENT/TRANSFER/COUNT: can be positive or negative
    quantity = Column(Integer, nullable=False)
    
    # Location information
    from_location_id = Column(String(36), nullable=False, index=True)
    to_location_id = Column(String(36), nullable=True)  # null for SALE, required for TRANSFER
    
    # Product and organization
    product_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    
    # User who recorded this movement
    recorded_by = Column(String(36), nullable=False)  # FK to User (user_id)
    
    # Optional references
    till_session_id = Column(String(36), nullable=True)  # For SALE movements from till
    sale_id = Column(String(36), nullable=True)  # For tracking which sale caused movement
    
    # Reason for movement (required for ADJUSTMENT, optional for others)
    reason = Column(Text, nullable=True)
    
    # Composite index for fast lookups by location and product
    __table_args__ = (
        Index('idx_movement_location_product', 'from_location_id', 'product_id'),
        Index('idx_movement_product_org', 'product_id', 'organization_id'),
        Index('idx_movement_created', 'created_at'),
        # Constraint: to_location_id required for TRANSFER, null for SALE
        CheckConstraint(
            "(type != 'TRANSFER' OR to_location_id IS NOT NULL) AND "
            "(type = 'TRANSFER' OR to_location_id IS NULL)",
            name='ck_transfer_location'
        ),
    )

    @staticmethod
    def create_sale(
        movement_id: str,
        from_location_id: str,
        product_id: str,
        organization_id: str,
        quantity: int,
        recorded_by: str,
        sale_id: str,
        till_session_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> 'InventoryMovement':
        """Create a SALE movement (stock out)."""
        return InventoryMovement(
            id=movement_id,
            type=MovementType.SALE.value,
            quantity=-abs(quantity),  # Always negative for SALE
            from_location_id=from_location_id,
            to_location_id=None,
            product_id=product_id,
            organization_id=organization_id,
            recorded_by=recorded_by,
            sale_id=sale_id,
            till_session_id=till_session_id,
            reason=reason or f"Sale recorded from till session {till_session_id}",
        )

    @staticmethod
    def create_adjustment(
        movement_id: str,
        location_id: str,
        product_id: str,
        organization_id: str,
        quantity: int,
        recorded_by: str,
        reason: str,
    ) -> 'InventoryMovement':
        """Create an ADJUSTMENT movement (inventory correction)."""
        return InventoryMovement(
            id=movement_id,
            type=MovementType.ADJUSTMENT.value,
            quantity=quantity,  # Can be positive or negative
            from_location_id=location_id,
            to_location_id=None,
            product_id=product_id,
            organization_id=organization_id,
            recorded_by=recorded_by,
            reason=reason,
        )

    @staticmethod
    def create_transfer(
        movement_id: str,
        from_location_id: str,
        to_location_id: str,
        product_id: str,
        organization_id: str,
        quantity: int,
        recorded_by: str,
        reason: Optional[str] = None,
    ) -> 'InventoryMovement':
        """Create a TRANSFER movement (stock move between locations)."""
        return InventoryMovement(
            id=movement_id,
            type=MovementType.TRANSFER.value,
            quantity=-abs(quantity),  # Negative for from_location
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            product_id=product_id,
            organization_id=organization_id,
            recorded_by=recorded_by,
            reason=reason or f"Transfer from {from_location_id} to {to_location_id}",
        )

    @staticmethod
    def create_count(
        movement_id: str,
        location_id: str,
        product_id: str,
        organization_id: str,
        quantity: int,
        recorded_by: str,
        reason: str,
    ) -> 'InventoryMovement':
        """Create a COUNT movement (physical count adjustment)."""
        return InventoryMovement(
            id=movement_id,
            type=MovementType.COUNT.value,
            quantity=quantity,  # Adjustment to match physical count
            from_location_id=location_id,
            to_location_id=None,
            product_id=product_id,
            organization_id=organization_id,
            recorded_by=recorded_by,
            reason=reason,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert movement to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "quantity": self.quantity,
            "from_location_id": self.from_location_id,
            "to_location_id": self.to_location_id,
            "product_id": self.product_id,
            "organization_id": self.organization_id,
            "recorded_by": self.recorded_by,
            "sale_id": self.sale_id,
            "till_session_id": self.till_session_id,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


class DiscrepancyRecord(Base):
    """
    Record of inventory discrepancies detected after sync.
    
    A discrepancy occurs when:
    expected_stock = last_audit_balance + movements_since_last_audit
    actual_stock = computed from ledger after sync
    If expected_stock ≠ actual_stock, a discrepancy is recorded.
    
    Statuses:
    - PENDING: Detected, awaiting reconciliation
    - RESOLVED: Administrator applied ADJUSTMENT to correct
    - WAIVED: Administrator accepted variance without adjustment
    """
    __tablename__ = "discrepancy_records"

    id = Column(String(36), primary_key=True)
    
    # Location and product information
    location_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), nullable=False, index=True)
    organization_id = Column(String(36), nullable=False, index=True)
    
    # Discrepancy amounts
    expected_qty = Column(Integer, nullable=False)
    actual_qty = Column(Integer, nullable=False)
    variance = Column(Integer, nullable=False)  # actual_qty - expected_qty
    
    # Tracking
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = Column(String(20), nullable=False, default=DiscrepancyStatus.PENDING.value)
    
    # Reference to contributing sales that caused variance
    # Stored as comma-separated IDs (e.g., "sale1,sale2,sale3")
    contributing_sale_ids = Column(Text, nullable=True)
    
    # Resolution metadata
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), nullable=True)  # FK to User
    resolution_reason = Column(Text, nullable=True)
    
    # Composite index for queries
    __table_args__ = (
        Index('idx_discrepancy_location_product', 'location_id', 'product_id'),
        Index('idx_discrepancy_org_status', 'organization_id', 'status'),
        Index('idx_discrepancy_detected', 'detected_at'),
    )

    def set_contributing_sales(self, sale_ids: List[str]) -> None:
        """Set contributing sale IDs from a list."""
        self.contributing_sale_ids = ",".join(sale_ids) if sale_ids else None

    def get_contributing_sales(self) -> List[str]:
        """Get contributing sale IDs as a list."""
        if not self.contributing_sale_ids:
            return []
        return self.contributing_sale_ids.split(",")

    def mark_resolved(self, resolved_by: str, reason: str) -> None:
        """Mark discrepancy as resolved."""
        self.status = DiscrepancyStatus.RESOLVED.value
        self.resolved_at = datetime.utcnow()
        self.resolved_by = resolved_by
        self.resolution_reason = reason

    def mark_waived(self, resolved_by: str, reason: str) -> None:
        """Mark discrepancy as waived (accepted without adjustment)."""
        self.status = DiscrepancyStatus.WAIVED.value
        self.resolved_at = datetime.utcnow()
        self.resolved_by = resolved_by
        self.resolution_reason = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert discrepancy record to dictionary."""
        return {
            "id": self.id,
            "location_id": self.location_id,
            "product_id": self.product_id,
            "organization_id": self.organization_id,
            "expected_qty": self.expected_qty,
            "actual_qty": self.actual_qty,
            "variance": self.variance,
            "detected_at": self.detected_at.isoformat(),
            "status": self.status,
            "contributing_sale_ids": self.get_contributing_sales(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_reason": self.resolution_reason,
        }


# Enforce immutability at SQLAlchemy level
@event.listens_for(InventoryMovement, "before_update")
def prevent_movement_update(mapper, connection, target):
    """Prevent UPDATE operations on InventoryMovement."""
    raise IntegrityError(
        "InventoryMovement records are immutable and cannot be updated. "
        "Create a new ADJUSTMENT movement instead.",
        None,
        None,
    )


@event.listens_for(InventoryMovement, "before_delete")
def prevent_movement_delete(mapper, connection, target):
    """Prevent DELETE operations on InventoryMovement."""
    raise IntegrityError(
        "InventoryMovement records are immutable and cannot be deleted. "
        "Create a compensating ADJUSTMENT movement instead.",
        None,
        None,
    )

"""Domain models for Tenga Inventory POS."""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, 
    Numeric, Text, Index, CheckConstraint, UniqueConstraint, event
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from src.database.config import Base


class BaseEntity(Base):
    """Abstract base entity with common columns."""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def organization_id(cls):
        """Every entity must belong to an organization (tenant isolation)."""
        return Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)


class Organization(Base):
    """Organization (tenant) aggregate root.
    
    Single organization per deployment. All records are scoped to organization_id.
    """
    __tablename__ = "organization"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    tills = relationship("Till", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", back_populates="organization", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="organization", cascade="all, delete-orphan")
    till_sessions = relationship("TillSession", back_populates="organization", cascade="all, delete-orphan")


class User(BaseEntity):
    """User entity with role context.
    
    Users are scoped to organization. Roles determine permissions.
    """
    __tablename__ = "user"
    __table_args__ = (
        Index("idx_org_email", "organization_id", "email", unique=True),
    )
    
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    full_name = Column(String(255))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="operator")  # operator, manager, admin
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    inventory_movements = relationship("InventoryMovement", back_populates="recorded_by", foreign_keys="InventoryMovement.recorded_by_id")
    till_sessions = relationship("TillSession", back_populates="operator")
    sales = relationship("Sale", back_populates="cashier")


class Location(BaseEntity):
    """Inventory location within organization.
    
    Represents a physical or logical inventory location (warehouse, store, branch).
    """
    __tablename__ = "location"
    __table_args__ = (
        Index("idx_org_code", "organization_id", "code", unique=True),
    )
    
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="locations")
    tills = relationship("Till", back_populates="location")
    inventory_movements = relationship("InventoryMovement", back_populates="location")
    stock = relationship("Stock", back_populates="location", cascade="all, delete-orphan")


class Product(BaseEntity):
    """Saleable item.
    
    Product definitions are organization-wide. Stock is tracked per location.
    """
    __tablename__ = "product"
    __table_args__ = (
        Index("idx_org_sku", "organization_id", "sku", unique=True),
    )
    
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price = Column(Numeric(12, 2), nullable=False)
    cost = Column(Numeric(12, 2))
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="products")
    inventory_movements = relationship("InventoryMovement", back_populates="product")
    stock = relationship("Stock", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")


class Till(BaseEntity):
    """POS operational entity (not device-bound).
    
    Represents a logical till/register. Can be used on different devices.
    """
    __tablename__ = "till"
    __table_args__ = (
        Index("idx_org_code_till", "organization_id", "code", unique=True),
    )
    
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="tills")
    location = relationship("Location", back_populates="tills")
    till_sessions = relationship("TillSession", back_populates="till", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="till")


class Subscription(BaseEntity):
    """Billing and subscription state.
    
    Skeleton for state machine (ACTIVE/GRACE/LIMITED). Transitions in T002.
    """
    __tablename__ = "subscription"
    
    plan = Column(String(50), nullable=False)  # e.g., BASIC, PROFESSIONAL
    term = Column(String(20), nullable=False)  # MONTHLY, ANNUAL
    state = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, GRACE, LIMITED, EXPIRED
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=False)
    grace_end_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")


class Stock(Base):
    """Stock quantity at location (derived view, not directly updatable).
    
    Computed from InventoryMovement ledger: SUM(IN) - SUM(OUT).
    This table is a computed view; do NOT allow direct updates.
    """
    __tablename__ = "stock"
    __table_args__ = (
        Index("idx_location_product", "location_id", "product_id", unique=True),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    last_movement_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    location = relationship("Location", back_populates="stock")
    product = relationship("Product", back_populates="stock")


class InventoryMovement(Base):
    """Immutable audit trail of inventory changes.
    
    CRITICAL: This table is append-only. No UPDATE or DELETE allowed after creation.
    Every movement is the authority on inventory state (not Stock table).
    Movements include: IN (purchase, adjustment), OUT (sale, adjustment).
    """
    __tablename__ = "inventory_movement"
    __table_args__ = (
        Index("idx_org_created", "organization_id", "created_at"),
        Index("idx_location_created", "location_id", "created_at"),
        Index("idx_product_created", "product_id", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False, index=True)
    
    movement_type = Column(String(20), nullable=False)  # IN, OUT
    quantity = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)  # PURCHASE, SALE, ADJUSTMENT, RETURN, etc.
    reference_id = Column(Integer)  # References sale_id, purchase_order_id, etc.
    reference_type = Column(String(50))  # SALE, PO, ADJUSTMENT, etc.
    
    recorded_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="inventory_movements")
    location = relationship("Location", back_populates="inventory_movements")
    product = relationship("Product", back_populates="inventory_movements")
    recorded_by = relationship("User", back_populates="inventory_movements", foreign_keys=[recorded_by_id])


# Trigger to prevent UPDATE/DELETE on InventoryMovement
@event.listens_for(InventoryMovement, "before_update")
def prevent_inventory_movement_update(mapper, connection, target):
    raise Exception("InventoryMovement records are immutable and cannot be updated")


@event.listens_for(InventoryMovement, "before_delete")
def prevent_inventory_movement_delete(mapper, connection, target):
    raise Exception("InventoryMovement records are immutable and cannot be deleted")


class Sale(BaseEntity):
    """Transaction record.
    
    Represents a completed sale. Details stored in SaleItem.
    """
    __tablename__ = "sale"
    __table_args__ = (
        Index("idx_till_created", "till_id", "created_at"),
        Index("idx_org_created_sale", "organization_id", "created_at"),
    )
    
    till_id = Column(Integer, ForeignKey("till.id"), nullable=False, index=True)
    cashier_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    total_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    payment_method = Column(String(50), nullable=False)  # CASH, CARD, MOBILE, etc.
    status = Column(String(20), nullable=False, default="COMPLETED")  # PENDING, COMPLETED, REFUNDED
    notes = Column(Text)
    
    # Relationships
    organization = relationship("Organization", back_populates="sales")
    till = relationship("Till", back_populates="sales")
    cashier = relationship("User", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(Base):
    """Item line in a sale."""
    __tablename__ = "sale_item"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_per_item = Column(Numeric(12, 2), default=0)
    total_price = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product", back_populates="sale_items")


class TillSession(BaseEntity):
    """Operational context for a till.
    
    Represents a till being opened and operated by an operator.
    Lifecycle operations (open, close, reconcile) in T006.
    """
    __tablename__ = "till_session"
    __table_args__ = (
        Index("idx_till_created_session", "till_id", "created_at"),
        Index("idx_operator_created", "operator_id", "created_at"),
    )
    
    till_id = Column(Integer, ForeignKey("till.id"), nullable=False, index=True)
    operator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    session_number = Column(String(100), nullable=False)  # Unique session identifier
    opening_balance = Column(Numeric(12, 2), nullable=False, default=0)
    closing_balance = Column(Numeric(12, 2))
    
    status = Column(String(20), nullable=False, default="OPEN")  # OPEN, CLOSED, SUSPENDED
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime)
    
    notes = Column(Text)
    
    # Relationships
    organization = relationship("Organization", back_populates="till_sessions")
    till = relationship("Till", back_populates="till_sessions")
    operator = relationship("User", back_populates="till_sessions")

"""SQLAlchemy ORM models for Tenga Inventory POS system."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Numeric, 
    ForeignKey, UniqueConstraint, Index, event, CheckConstraint
)
from sqlalchemy.orm import relationship
from src.database.config import Base


class BaseEntity(Base):
    """Base model for all entities with common timestamps."""
    __abstract__ = True
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Organization(BaseEntity):
    """Organization entity - root tenant for multi-tenancy."""
    __tablename__ = "organization"
    __table_args__ = (
        Index('ix_organization_code', 'code'),
        Index('ix_organization_is_active', 'is_active'),
        Index('ix_organization_name', 'name'),
    )
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    tills = relationship("Till", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    stock = relationship("Stock", back_populates="organization", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", back_populates="organization", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="organization", cascade="all, delete-orphan")
    till_sessions = relationship("TillSession", back_populates="organization", cascade="all, delete-orphan")


class User(BaseEntity):
    """User entity - organization member with role-based access."""
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint('email', 'organization_id', name='ix_org_email'),
        Index('ix_user_email', 'email'),
        Index('ix_user_is_active', 'is_active'),
        Index('ix_user_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    email = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    full_name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # operator, manager, admin
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    inventory_movements = relationship("InventoryMovement", foreign_keys="InventoryMovement.recorded_by_id", back_populates="recorded_by")
    sales = relationship("Sale", foreign_keys="Sale.cashier_id", back_populates="cashier")
    till_sessions = relationship("TillSession", foreign_keys="TillSession.operator_id", back_populates="operator")


class Location(BaseEntity):
    """Location entity - physical store location within organization."""
    __tablename__ = "location"
    __table_args__ = (
        UniqueConstraint('code', 'organization_id', name='ix_org_code'),
        Index('ix_location_is_active', 'is_active'),
        Index('ix_location_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="locations")
    tills = relationship("Till", back_populates="location", cascade="all, delete-orphan")
    stock = relationship("Stock", back_populates="location", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", foreign_keys="InventoryMovement.location_id", back_populates="location")


class Product(BaseEntity):
    """Product entity - inventory item within organization."""
    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint('sku', 'organization_id', name='ix_org_sku'),
        Index('ix_product_is_active', 'is_active'),
        Index('ix_product_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    price = Column(Numeric(precision=12, scale=2), nullable=False)
    cost = Column(Numeric(precision=12, scale=2), nullable=True)
    barcode = Column(String(100), nullable=True)  # Added for Phase B: barcode support
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="products")
    stock = relationship("Stock", back_populates="product", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", foreign_keys="InventoryMovement.product_id", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")


class Till(BaseEntity):
    """Till entity - point of sale terminal."""
    __tablename__ = "till"
    __table_args__ = (
        UniqueConstraint('code', 'organization_id', name='ix_org_code_till'),
        Index('ix_till_is_active', 'is_active'),
        Index('ix_till_location_id', 'location_id'),
        Index('ix_till_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="tills")
    location = relationship("Location", back_populates="tills")
    sales = relationship("Sale", back_populates="till", cascade="all, delete-orphan")
    till_sessions = relationship("TillSession", back_populates="till", cascade="all, delete-orphan")


class Subscription(BaseEntity):
    """Subscription entity - SaaS subscription for organization."""
    __tablename__ = "subscription"
    __table_args__ = (
        Index('ix_subscription_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    plan = Column(String(50), nullable=False)  # e.g., "starter", "professional"
    term = Column(String(20), nullable=False)  # e.g., "monthly", "annual"
    state = Column(String(50), nullable=False)  # e.g., "active", "expired", "cancelled"
    start_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    grace_end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")


class Stock(BaseEntity):
    """Stock entity - derived view of current inventory at location."""
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint('location_id', 'product_id', name='ix_location_product'),
        Index('ix_stock_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    last_movement_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="stock")
    location = relationship("Location", back_populates="stock")
    product = relationship("Product", back_populates="stock")


class InventoryMovement(BaseEntity):
    """InventoryMovement entity - append-only audit trail of stock changes."""
    __tablename__ = "inventory_movement"
    __table_args__ = (
        Index('ix_inventory_movement_created_at', 'created_at'),
        Index('ix_inventory_movement_location_created', 'location_id', 'created_at'),
        Index('ix_inventory_movement_organization_created', 'organization_id', 'created_at'),
        Index('ix_inventory_movement_product_created', 'product_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    movement_type = Column(String(20), nullable=False)  # SALE, ADJUSTMENT, TRANSFER, COUNT
    quantity = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)  # Canonical reason code: PHYSICAL_COUNT_DISCREPANCY, DAMAGE, SHRINKAGE, ADJUSTMENT
    reference_id = Column(Integer, nullable=True)  # e.g., sale_id, till_session_id
    reference_type = Column(String(50), nullable=True)  # e.g., "sale", "physical_count"
    recorded_by_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="inventory_movements")
    location = relationship("Location", foreign_keys="InventoryMovement.location_id", back_populates="inventory_movements")
    product = relationship("Product", foreign_keys="InventoryMovement.product_id", back_populates="inventory_movements")
    recorded_by = relationship("User", foreign_keys="InventoryMovement.recorded_by_id", back_populates="inventory_movements")


class Sale(BaseEntity):
    """Sale entity - transaction record."""
    __tablename__ = "sale"
    __table_args__ = (
        Index('ix_sale_created_till', 'till_id', 'created_at'),
        Index('ix_sale_organization_created', 'organization_id', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    till_id = Column(Integer, ForeignKey('till.id'), nullable=False)
    cashier_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    total_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    discount_amount = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    tax_amount = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    payment_method = Column(String(50), nullable=False)  # cash, card, mobile_money
    status = Column(String(20), nullable=False, default="completed")  # completed, pending, cancelled
    notes = Column(Text, nullable=True)
    till_session_id = Column(Integer, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="sales")
    till = relationship("Till", back_populates="sales")
    cashier = relationship("User", foreign_keys="Sale.cashier_id", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(BaseEntity):
    """SaleItem entity - line item in a sale."""
    __tablename__ = "sale_item"
    __table_args__ = (
        Index('ix_sale_item_sale_id', 'sale_id'),
    )
    
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sale.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(precision=12, scale=2), nullable=False)
    discount_per_item = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    total_price = Column(Numeric(precision=12, scale=2), nullable=False)
    
    # Relationships
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product", back_populates="sale_items")


class TillSession(BaseEntity):
    """TillSession entity - till opening/closing session."""
    __tablename__ = "till_session"
    __table_args__ = (
        Index('ix_till_session_created_session', 'till_id', 'created_at'),
        Index('ix_till_session_operator_created', 'operator_id', 'created_at'),
        Index('ix_till_session_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    till_id = Column(Integer, ForeignKey('till.id'), nullable=False)
    operator_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    session_number = Column(String(100), nullable=False)
    opening_balance = Column(Numeric(precision=12, scale=2), nullable=False)
    closing_balance = Column(Numeric(precision=12, scale=2), nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open, closed
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="till_sessions")
    till = relationship("Till", back_populates="till_sessions")
    operator = relationship("User", foreign_keys="TillSession.operator_id", back_populates="till_sessions")

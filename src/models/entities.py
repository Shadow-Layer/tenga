"""SQLAlchemy ORM models for Tenga Inventory POS system."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Numeric, 
    ForeignKey, UniqueConstraint, Index, event, CheckConstraint, text
)
from sqlalchemy.exc import IntegrityError
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
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    region = Column(String(100), nullable=True)
    timezone = Column(String(100), nullable=False, default="UTC")
    currency_code = Column(String(3), nullable=True, default="USD")
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="organization", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    tills = relationship("Till", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    stock = relationship("Stock", back_populates="organization", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", back_populates="organization", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="organization", cascade="all, delete-orphan")
    till_sessions = relationship("TillSession", back_populates="organization", cascade="all, delete-orphan")
    tax_rules = relationship("TaxRule", back_populates="organization")
    data_imports = relationship(
        "DataImportBatch",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    payment_attempts = relationship("PaymentAttempt", back_populates="organization")
    offline_operations = relationship("OfflineOperation", back_populates="organization")


class TaxRule(BaseEntity):
    """Organization-scoped tax rule for product pricing."""
    __tablename__ = "tax_rule"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_tax_rule_org_name"),
        CheckConstraint("rate >= 0 AND rate <= 100", name="ck_tax_rule_rate_range"),
        Index("ix_tax_rule_organization_active", "organization_id", "is_active"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    name = Column(String(100), nullable=False)
    rate = Column(Numeric(precision=5, scale=2), nullable=False)
    tax_inclusive = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", back_populates="tax_rules")


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
    employee = relationship("Employee", back_populates="user", uselist=False)
    inventory_movements = relationship("InventoryMovement", foreign_keys="InventoryMovement.recorded_by_id", back_populates="recorded_by")
    sales = relationship("Sale", foreign_keys="Sale.cashier_id", back_populates="cashier")
    till_sessions = relationship("TillSession", foreign_keys="TillSession.operator_id", back_populates="operator")


class Employee(BaseEntity):
    """Organization employee record, optionally linked to a login account."""
    __tablename__ = "employee"
    __table_args__ = (
        UniqueConstraint("organization_id", "employee_number", name="uq_employee_org_number"),
        UniqueConstraint("user_id", name="uq_employee_user"),
        Index("ix_employee_organization_active", "organization_id", "is_active"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    employee_number = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    title = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    archived_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="employees")
    user = relationship("User", back_populates="employee")
    location_assignments = relationship(
        "EmployeeLocationAssignment",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    till_assignments = relationship(
        "EmployeeTillAssignment",
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class EmployeeLocationAssignment(BaseEntity):
    """Location access assigned to an employee."""
    __tablename__ = "employee_location_assignment"
    __table_args__ = (
        Index(
            "uq_employee_location_active",
            "employee_id",
            "location_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    employee = relationship("Employee", back_populates="location_assignments")
    location = relationship("Location")


class EmployeeTillAssignment(BaseEntity):
    """Till access assigned to an employee."""
    __tablename__ = "employee_till_assignment"
    __table_args__ = (
        Index(
            "uq_employee_till_active",
            "employee_id",
            "till_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=False)
    till_id = Column(Integer, ForeignKey("till.id"), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    employee = relationship("Employee", back_populates="till_assignments")
    till = relationship("Till")


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
    unit_of_measure = Column(String(50), nullable=False, default="each")
    minimum_stock_level = Column(Integer, nullable=False, default=0)
    tax_rule_id = Column(Integer, ForeignKey("tax_rule.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="products")
    stock = relationship("Stock", back_populates="product", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", foreign_keys="InventoryMovement.product_id", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")
    tax_rule = relationship("TaxRule")


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
        UniqueConstraint(
            "organization_id",
            "device_id",
            "device_local_id",
            name="uq_inventory_movement_device_operation",
        ),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('location.id'), nullable=False)
    to_location_id = Column(Integer, ForeignKey("location.id"), nullable=True)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    movement_type = Column(
        String(20), nullable=False, default="ADJUSTMENT"
    )  # SALE, ADJUSTMENT, TRANSFER, COUNT
    quantity = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)  # Canonical reason code: PHYSICAL_COUNT_DISCREPANCY, DAMAGE, SHRINKAGE, ADJUSTMENT
    notes = Column(Text, nullable=True)
    external_reference = Column(String(255), nullable=True)
    reference_id = Column(Integer, nullable=True)  # e.g., sale_id, till_session_id
    reference_type = Column(String(50), nullable=True)  # e.g., "sale", "physical_count"
    recorded_by_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    recorded_by_employee_id = Column(Integer, ForeignKey("employee.id"), nullable=True)
    unit_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    currency_code = Column(String(3), nullable=True)
    device_id = Column(String(100), nullable=True)
    device_local_id = Column(String(100), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="inventory_movements")
    location = relationship("Location", foreign_keys="InventoryMovement.location_id", back_populates="inventory_movements")
    destination_location = relationship("Location", foreign_keys=[to_location_id])
    product = relationship("Product", foreign_keys="InventoryMovement.product_id", back_populates="inventory_movements")
    recorded_by = relationship("User", foreign_keys="InventoryMovement.recorded_by_id", back_populates="inventory_movements")
    recorded_by_employee = relationship("Employee", foreign_keys=[recorded_by_employee_id])


class Sale(BaseEntity):
    """Sale entity - transaction record."""
    __tablename__ = "sale"
    __table_args__ = (
        Index('ix_sale_created_till', 'till_id', 'created_at'),
        Index('ix_sale_organization_created', 'organization_id', 'created_at'),
        Index('ix_sale_fiscal_number', 'fiscal_number'),
        Index('ix_sale_fiscal_status', 'fiscal_status'),
        UniqueConstraint(
            'organization_id',
            'external_reference',
            name='uq_sale_org_external_reference',
        ),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    till_id = Column(Integer, ForeignKey('till.id'), nullable=False)
    cashier_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    total_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    discount_amount = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    tax_amount = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    amount_tendered = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    change_given = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    payment_method = Column(String(50), nullable=False)  # cash, card, mobile_money
    status = Column(String(20), nullable=False, default="completed")  # completed, pending, cancelled
    notes = Column(Text, nullable=True)
    till_session_id = Column(Integer, ForeignKey("till_session.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=True)
    currency_code = Column(String(3), nullable=True)
    # Fiscal integration fields (TengaVFD)
    fiscal_number = Column(String(50), nullable=True, unique=True)  # ZIMRA-assigned fiscal receipt #
    fiscal_status = Column(String(20), nullable=False, default="pending")  # pending, submitted, acknowledged, failed
    fiscal_status_updated_at = Column(DateTime, nullable=True)
    fiscal_submission_attempts = Column(Integer, nullable=False, default=0)
    source_type = Column(String(30), nullable=False, default="LIVE", server_default="LIVE")
    external_reference = Column(String(255), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="sales")
    till = relationship("Till", back_populates="sales")
    cashier = relationship("User", foreign_keys="Sale.cashier_id", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale", cascade="all, delete-orphan")
    payment_attempts = relationship("PaymentAttempt", back_populates="sale", cascade="all, delete-orphan")
    fiscal_submissions = relationship("FiscalSubmission", back_populates="sale", cascade="all, delete-orphan")
    receipt_audits = relationship("ReceiptAudit", back_populates="sale", cascade="all, delete-orphan")
    location = relationship("Location")
    till_session = relationship("TillSession", back_populates="sales")


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
    tax_rule_id = Column(Integer, nullable=True)
    tax_rate = Column(Numeric(precision=5, scale=2), nullable=False, default=0)
    tax_inclusive = Column(Boolean, nullable=False, default=False)
    tax_amount = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    
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
        Index(
            "uq_till_session_one_open_per_till",
            "till_id",
            unique=True,
            sqlite_where=text("upper(status) = 'OPEN'"),
            postgresql_where=text("upper(status) = 'OPEN'"),
        ),
    )
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    till_id = Column(Integer, ForeignKey('till.id'), nullable=False)
    operator_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    session_number = Column(String(100), nullable=False)
    opening_balance = Column(Numeric(precision=12, scale=2), nullable=False)
    closing_balance = Column(Numeric(precision=12, scale=2), nullable=True)
    expected_closing_balance = Column(Numeric(precision=12, scale=2), nullable=True)
    cash_variance = Column(Numeric(precision=12, scale=2), nullable=True)
    currency_code = Column(String(3), nullable=True)
    closed_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open, closed
    opened_at = Column(DateTime, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="till_sessions")
    till = relationship("Till", back_populates="till_sessions")
    operator = relationship("User", foreign_keys="TillSession.operator_id", back_populates="till_sessions")
    closed_by = relationship("User", foreign_keys=[closed_by_id])
    sales = relationship("Sale", back_populates="till_session")
    cash_movements = relationship("TillCashMovement", back_populates="till_session")


class TillCashMovement(BaseEntity):
    """Append-only cash in/out event recorded against an open till session."""
    __tablename__ = "till_cash_movement"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "operation_id",
            name="uq_till_cash_movement_operation",
        ),
        CheckConstraint("amount > 0", name="ck_till_cash_movement_positive_amount"),
        CheckConstraint(
            "direction IN ('CASH_IN', 'CASH_OUT')",
            name="ck_till_cash_movement_direction",
        ),
        Index(
            "ix_till_cash_movement_session_created",
            "organization_id",
            "till_session_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    till_id = Column(Integer, ForeignKey("till.id"), nullable=False)
    till_session_id = Column(Integer, ForeignKey("till_session.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employee.id"), nullable=True)
    operation_id = Column(String(100), nullable=False)
    direction = Column(String(10), nullable=False)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    reason = Column(String(255), nullable=False)
    reference = Column(String(255), nullable=True)

    till_session = relationship("TillSession", back_populates="cash_movements")
    actor = relationship("User")
    employee = relationship("Employee")


@event.listens_for(TillCashMovement, "before_update")
def prevent_till_cash_movement_update(mapper, connection, target):
    raise IntegrityError(
        "TillCashMovement records are immutable.",
        None,
        None,
    )


@event.listens_for(TillCashMovement, "before_delete")
def prevent_till_cash_movement_delete(mapper, connection, target):
    raise IntegrityError(
        "TillCashMovement records are immutable.",
        None,
        None,
    )


class Payment(BaseEntity):
    """Persisted tender record associated with a sale."""
    __tablename__ = "payment"
    __table_args__ = (
        Index("ix_payment_organization_created", "organization_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False)
    payment_method = Column(String(30), nullable=False)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    amount_tendered = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    change_given = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    currency_code = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False, default="COMPLETED")
    provider_reference = Column(String(255), nullable=True)

    sale = relationship("Sale", back_populates="payments")
    organization = relationship("Organization")


class PaymentAttempt(BaseEntity):
    """Server-side payment provider attempt; browser return never settles it."""
    __tablename__ = "payment_attempt"
    __table_args__ = (
        UniqueConstraint("organization_id", "merchant_reference", name="uq_payment_attempt_merchant_ref"),
        UniqueConstraint("provider_reference", name="uq_payment_attempt_provider_ref"),
        Index("ix_payment_attempt_org_status", "organization_id", "status"),
        Index(
            "uq_payment_attempt_retry_parent",
            "retry_of_attempt_id",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False)
    retry_of_attempt_id = Column(
        Integer,
        ForeignKey("payment_attempt.id", name="fk_payment_attempt_retry_parent"),
        nullable=True,
    )
    till_session_id = Column(Integer, ForeignKey("till_session.id"), nullable=False)
    initiated_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    provider = Column(String(30), nullable=False)
    payment_method = Column(String(30), nullable=False)
    merchant_reference = Column(String(100), nullable=False)
    provider_reference = Column(String(255), nullable=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    currency_code = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    redirect_url = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)

    organization = relationship("Organization", back_populates="payment_attempts")
    sale = relationship("Sale", back_populates="payment_attempts")
    till_session = relationship("TillSession")
    initiated_by = relationship("User")


class FiscalSubmission(BaseEntity):
    """Audited attempt to submit a completed sale to the external fiscal boundary."""
    __tablename__ = "fiscal_submission"
    __table_args__ = (
        UniqueConstraint("sale_id", "attempt_number", name="uq_fiscal_submission_attempt"),
        Index("ix_fiscal_submission_org_status", "organization_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    request_reference = Column(String(100), nullable=False)
    fiscal_number = Column(String(100), nullable=True)
    request_payload = Column(Text, nullable=True)
    response_payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    sale = relationship("Sale", back_populates="fiscal_submissions")
    organization = relationship("Organization")


class ReceiptAudit(BaseEntity):
    """Audit record for receipt generation, retrieval or reprint."""
    __tablename__ = "receipt_audit"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    action = Column(String(20), nullable=False)

    sale = relationship("Sale", back_populates="receipt_audits")
    organization = relationship("Organization")
    actor = relationship("User")


class OfflineOperation(BaseEntity):
    """Idempotency and reconciliation envelope for durable offline events."""
    __tablename__ = "offline_operation"
    __table_args__ = (
        UniqueConstraint("organization_id", "device_id", "operation_id", name="uq_offline_operation_identity"),
        Index("ix_offline_operation_org_status", "organization_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    device_id = Column(String(100), nullable=False)
    operation_id = Column(String(100), nullable=False)
    operation_type = Column(String(30), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    result_payload = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="offline_operations")
    actor = relationship("User")


class InventoryCount(BaseEntity):
    """Physical inventory count header; stock changes only on reconciliation."""
    __tablename__ = "inventory_count"
    __table_args__ = (
        Index("ix_inventory_count_org_status", "organization_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    reconciled_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    status = Column(String(20), nullable=False, default="DRAFT")
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reconciled_at = Column(DateTime, nullable=True)

    lines = relationship("InventoryCountLine", back_populates="count", cascade="all, delete-orphan")
    organization = relationship("Organization")
    location = relationship("Location")
    created_by = relationship("User", foreign_keys=[created_by_id])
    reconciled_by = relationship("User", foreign_keys=[reconciled_by_id])


class InventoryCountLine(BaseEntity):
    """Expected and observed quantity for a product in a physical count."""
    __tablename__ = "inventory_count_line"
    __table_args__ = (
        UniqueConstraint("count_id", "product_id", name="uq_inventory_count_product"),
    )

    id = Column(Integer, primary_key=True)
    count_id = Column(Integer, ForeignKey("inventory_count.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    expected_quantity = Column(Integer, nullable=False)
    observed_quantity = Column(Integer, nullable=True)
    reconciled_movement_id = Column(Integer, ForeignKey("inventory_movement.id"), nullable=True)

    count = relationship("InventoryCount", back_populates="lines")
    product = relationship("Product")
    reconciled_movement = relationship("InventoryMovement")


class InventoryTransfer(BaseEntity):
    """Atomic stock transfer identity shared by source and destination movements."""
    __tablename__ = "inventory_transfer"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "device_id",
            "device_local_id",
            name="uq_inventory_transfer_device_operation",
        ),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    source_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("location.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    device_id = Column(String(100), nullable=True)
    device_local_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="COMPLETED")
    reason = Column(String(100), nullable=False)

    organization = relationship("Organization")
    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    created_by = relationship("User")


class InventoryTransferLine(BaseEntity):
    """Product and quantity included in an atomic stock transfer."""
    __tablename__ = "inventory_transfer_line"

    id = Column(Integer, primary_key=True)
    transfer_id = Column(Integer, ForeignKey("inventory_transfer.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    quantity = Column(Integer, nullable=False)

    transfer = relationship("InventoryTransfer")
    product = relationship("Product")


class DataImportBatch(BaseEntity):
    """Audit and idempotency record for a committed setup CSV import."""
    __tablename__ = "data_import_batch"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "import_type",
            "content_sha256",
            name="uq_data_import_org_type_hash",
        ),
        Index("ix_data_import_organization_created", "organization_id", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    import_type = Column(String(30), nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    row_count = Column(Integer, nullable=False)

    organization = relationship("Organization", back_populates="data_imports")
    created_by = relationship("User")


@event.listens_for(InventoryMovement, "before_update")
def prevent_inventory_movement_update(mapper, connection, target):
    raise IntegrityError(
        "InventoryMovement records are immutable. Record a compensating movement instead.",
        None,
        None,
    )


@event.listens_for(InventoryMovement, "before_delete")
def prevent_inventory_movement_delete(mapper, connection, target):
    raise IntegrityError(
        "InventoryMovement records are immutable. Record a compensating movement instead.",
        None,
        None,
    )

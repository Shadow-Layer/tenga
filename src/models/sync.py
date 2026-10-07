"""Sync protocol models for offline operation and device state reconciliation."""
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from src.database import Base


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class TransactionType(str, Enum):
    """Types of transactions that can be synced."""
    SALE = "sale"
    MOVEMENT = "movement"


class TransactionStatus(str, Enum):
    """Status of an individual transaction in a sync batch."""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


class SubscriptionState(str, Enum):
    """Subscription states for grace period handling."""
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"


class SyncLog(Base):
    """Master log of all sync events for audit trail and conflict detection."""
    __tablename__ = "sync_logs"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(100), nullable=False, index=True)
    batch_id = Column(String(100), nullable=False, index=True)
    batch_size = Column(Integer, nullable=False)
    status = Column(SQLEnum(SyncStatus), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    organization_id = Column(String(36), nullable=True)
    
    # Cached response for idempotency
    cached_response_json = Column(JSON, nullable=True)
    
    # Relationship to batch transactions
    batch_transactions = relationship("SyncBatchTransaction", back_populates="sync_log", cascade="all, delete-orphan")
    
    # Metadata about the sync
    sync_duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)


class SyncBatchTransaction(Base):
    """Individual transaction record within a sync batch."""
    __tablename__ = "sync_batch_transactions"

    id = Column(String(36), primary_key=True)
    sync_log_id = Column(String(36), ForeignKey("sync_logs.id"), nullable=False, index=True)
    transaction_sequence = Column(Integer, nullable=False)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    status = Column(SQLEnum(TransactionStatus), nullable=False)
    
    # Transaction payload (stored as JSON for flexibility)
    transaction_data = Column(JSON, nullable=False)
    
    # Application result
    applied_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Reference to applied entity (if applicable)
    applied_entity_id = Column(String(36), nullable=True)
    applied_entity_type = Column(String(50), nullable=True)
    
    sync_log = relationship("SyncLog", back_populates="batch_transactions")


class DeviceSyncCache(Base):
    """Device-side cache of subscription state and last sync metadata."""
    __tablename__ = "device_sync_caches"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Last successful sync
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_log_id = Column(String(36), ForeignKey("sync_logs.id"), nullable=True)
    
    # Cached subscription state
    cached_subscription_state = Column(SQLEnum(SubscriptionState), nullable=True)
    cached_state_expires_at = Column(DateTime, nullable=True)
    
    # Device metadata
    device_name = Column(String(255), nullable=True)
    last_device_timestamp = Column(DateTime, nullable=True)
    
    # Reconciliation
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncIdempotencyCache(Base):
    """Cache for idempotent sync responses to prevent duplicate processing."""
    __tablename__ = "sync_idempotency_caches"

    id = Column(String(36), primary_key=True)
    device_id = Column(String(100), nullable=False, index=True)
    batch_id = Column(String(100), nullable=False, index=True)
    
    # Composite unique key for deduplication
    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint(
            device_id, batch_id, name="uq_device_batch"
        ),
    )
    
    # Cached response
    sync_log_id = Column(String(36), ForeignKey("sync_logs.id"), nullable=False)
    response_json = Column(JSON, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)  # For cleanup of old cache entries

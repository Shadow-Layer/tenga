"""Pydantic schemas for sync protocol requests and responses."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    """Types of transactions that can be synced."""
    SALE = "sale"
    MOVEMENT = "movement"


class SubscriptionState(str, Enum):
    """Subscription states for grace period handling."""
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"


class LocalStateSnapshot(BaseModel):
    """Device's cached view of subscription state and sync metadata."""
    cached_subscription_state: Optional[SubscriptionState] = None
    cached_state_expires_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    device_name: Optional[str] = None
    device_timestamp: datetime = Field(default_factory=datetime.utcnow)


class SyncTransactionData(BaseModel):
    """A single transaction from device (sale, movement, etc.)."""
    transaction_id: str = Field(..., description="Device-generated unique transaction ID for deduplication")
    transaction_type: TransactionType = Field(..., description="Type of transaction (sale or movement)")
    sequence_number: int = Field(..., description="Sequence number for ordering within batch")
    
    # Common fields for all transaction types
    product_id: str
    quantity: float
    timestamp: datetime
    user_id: Optional[str] = None
    
    # Movement-specific fields
    location_id: Optional[str] = None
    from_location_id: Optional[str] = None
    to_location_id: Optional[str] = None
    movement_type: Optional[str] = None  # e.g., "receipt", "issue", "transfer"
    reason: Optional[str] = None
    
    # Sale-specific fields
    till_id: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None


class SyncRequestPayload(BaseModel):
    """Complete sync request from device."""
    device_id: str = Field(..., description="Unique device identifier")
    batch_id: str = Field(..., description="Unique batch identifier for deduplication")
    local_state_snapshot: LocalStateSnapshot
    transaction_batch: List[SyncTransactionData] = Field(default_factory=list)
    organization_id: Optional[str] = None


class TransactionAcknowledgment(BaseModel):
    """Result of applying a single transaction."""
    transaction_id: str
    status: str = Field(..., description="'applied' or 'failed'")
    applied_entity_id: Optional[str] = None
    error_message: Optional[str] = None


class StateTransition(BaseModel):
    """Notification of subscription state change on server."""
    previous_state: SubscriptionState
    new_state: SubscriptionState
    transition_reason: str
    grace_end_date: Optional[datetime] = None
    effective_at: datetime = Field(default_factory=datetime.utcnow)


class SyncResponsePayload(BaseModel):
    """Complete sync response from server."""
    sync_id: str = Field(..., description="Unique sync operation ID")
    device_id: str
    batch_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Current server state
    server_subscription_state: SubscriptionState
    server_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # State change notification (if subscription state changed)
    state_transitions: Optional[List[StateTransition]] = None
    
    # Batch result
    batch_status: str = Field(..., description="'success', 'partial_failure', or 'duplicate'")
    batch_size: int
    transactions_acknowledged: int
    transactions_applied: int
    transactions_failed: int
    
    # Per-transaction results
    transaction_results: List[TransactionAcknowledgment]
    
    # Error details if any
    error_message: Optional[str] = None


class SyncServerState(BaseModel):
    """Simplified server state for sync response."""
    organization_id: str
    subscription_state: SubscriptionState
    subscription_expires_at: Optional[datetime] = None
    last_sync_id: str
    last_sync_timestamp: datetime


class SyncBatchItem(BaseModel):
    """A single item in a batch sync request."""
    batch_id: str = Field(..., description="Batch identifier")
    sequence: int = Field(..., description="Sequence number within batch")
    action: str = Field(..., description="Action to perform (e.g., SALE_COMMIT)")
    payload: Dict[str, Any] = Field(..., description="Action payload")


class SyncBatchCreate(BaseModel):
    """Request to submit a batch of offline transactions."""
    device_id: str = Field(..., description="Device identifier")
    organization_id: int = Field(..., description="Organization ID")
    items: List[SyncBatchItem] = Field(..., description="Batch items to sync")


class SyncBatchResponse(BaseModel):
    """Response for submitted batch."""
    id: str = Field(..., description="Batch ID")
    device_id: str = Field(..., description="Device ID")
    organization_id: int = Field(..., description="Organization ID")
    status: str = Field(..., description="Status: PENDING, PROCESSING, COMPLETED, FAILED")
    processed_items: int = Field(default=0, description="Number of processed items")
    total_items: int = Field(..., description="Total number of items in batch")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="List of errors if any")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    updated_at: Optional[datetime] = None


class SubscriptionStateSync(BaseModel):
    """Subscription state for device sync."""
    state: str = Field(..., description="State: ACTIVE, GRACE, or LIMITED")
    expiry_date: Optional[datetime] = None
    grace_end_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    operational: bool = Field(..., description="Whether subscription is operational")


class CacheUpdateRequest(BaseModel):
    """Request to update device cache."""
    device_id: str = Field(..., description="Device identifier")
    organization_id: int = Field(..., description="Organization ID")
    subscription_state: SubscriptionStateSync = Field(..., description="Subscription state to cache")


class CachedSubscriptionStateResponse(BaseModel):
    """Response for cached subscription state update."""
    id: int = Field(..., description="Cache record ID")
    device_id: str = Field(..., description="Device ID")
    organization_id: int = Field(..., description="Organization ID")
    state: str = Field(..., description="Cached state")
    last_sync_at: datetime = Field(..., description="Last sync timestamp")

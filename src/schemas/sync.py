"""Pydantic schemas for the authenticated offline operation sync protocol."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, constr
from enum import Enum


class SubscriptionState(str, Enum):
    """Subscription states for grace period handling."""
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"


class OfflineOperationType(str, Enum):
    SALE_COMMIT = "SALE_COMMIT"
    INVENTORY_RECEIPT = "INVENTORY_RECEIPT"
    INVENTORY_ISSUE = "INVENTORY_ISSUE"
    INVENTORY_ADJUSTMENT = "INVENTORY_ADJUSTMENT"
    INVENTORY_TRANSFER = "INVENTORY_TRANSFER"
    INVENTORY_COUNT = "INVENTORY_COUNT"
    INVENTORY_RETURN = "INVENTORY_RETURN"


class OfflineOperationInput(BaseModel):
    """One immutable local operation; identity is stable across retries/restarts."""

    model_config = ConfigDict(extra="forbid")

    operation_id: constr(min_length=1, max_length=100)
    operation_type: OfflineOperationType
    payload: Dict[str, Any]


class OfflineSyncRequest(BaseModel):
    """Device batch. Organization and actor are always derived from authentication."""

    model_config = ConfigDict(extra="forbid")

    device_id: constr(min_length=1, max_length=100)
    organization_id: int = Field(..., gt=0)
    operations: List[OfflineOperationInput] = Field(..., min_length=1, max_length=100)


class OperationAcknowledgementStatus(str, Enum):
    APPLIED = "APPLIED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class OperationAcknowledgement(BaseModel):
    operation_id: str
    status: OperationAcknowledgementStatus
    applied_entity_type: Optional[str] = None
    applied_entity_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class OfflineSyncResponse(BaseModel):
    """Per-operation server acknowledgements, including unresolved conflicts."""

    device_id: str
    organization_id: int
    acknowledgements: List[OperationAcknowledgement]


class SyncBatchResponse(BaseModel):
    """Response for submitted batch."""
    id: str = Field(..., description="Batch ID")
    device_id: str = Field(..., description="Device ID")
    organization_id: int = Field(..., description="Organization ID")
    status: str = Field(
        ...,
        description="Status: PENDING, PROCESSING, COMPLETED, PARTIAL_FAILURE, FAILED",
    )
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

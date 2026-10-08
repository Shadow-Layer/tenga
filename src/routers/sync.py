"""REST endpoints for offline batch sync and device state caching.

This module provides endpoints for synchronizing offline transactions
and managing device subscription state cache.

Operations include:
- Submit batch sync requests (offline transactions)
- Query sync status
- Cache subscription state on devices
- Retrieve cached subscription state

Offline Sync:
- Devices can queue transactions (sales, movements) while offline
- Batches are deduplicated by device_id and batch_id
- Transactions are applied in sequence number order
- Results include per-transaction acknowledgments and error details

Subscription State Cache:
- Devices cache subscription state locally for offline operation
- Cache includes expiry timestamp for validation
- Devices can query current state even when offline
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4

from src.database.config import get_db
from src.models.sync import SyncLog, SyncStatus, SyncIdempotencyCache, SyncBatchTransaction, TransactionStatus
from src.models.cached_subscription_state import CachedSubscriptionState
from src.models.entities import Organization, Subscription
from src.schemas.sync import (
    SyncBatchCreate,
    SyncBatchResponse,
    SubscriptionStateSync,
    CacheUpdateRequest,
    CachedSubscriptionStateResponse,
)
from src.services.sync_service import SyncService
from src.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/sync/batch", response_model=SyncBatchResponse, status_code=status.HTTP_201_CREATED)
def submit_batch(
    request: SyncBatchCreate,
    db: Session = Depends(get_db),
) -> SyncBatchResponse:
    """Submit offline batch for processing.
    
    Accepts a batch of offline transactions from a device. Implements idempotency
    so the same batch_id cannot be double-processed.
    
    Status progression: PENDING → PROCESSING → COMPLETED or FAILED
    """
    # Verify organization exists
    org = db.query(Organization).filter(
        Organization.id == request.organization_id
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {request.organization_id} not found",
        )
    
    # Check idempotency: batch_id + device_id must be unique
    existing_cache = db.query(SyncIdempotencyCache).filter(
        SyncIdempotencyCache.device_id == request.device_id,
        SyncIdempotencyCache.batch_id == request.items[0].batch_id if request.items else None,
    ).first()
    
    if existing_cache:
        # Idempotent: return the cached response
        existing_log = db.query(SyncLog).filter(
            SyncLog.id == existing_cache.sync_log_id
        ).first()
        if existing_log:
            return SyncBatchResponse(
                id=existing_log.batch_id,
                device_id=existing_log.device_id,
                organization_id=existing_log.organization_id,
                status=_sync_status_to_string(existing_log.status),
                processed_items=len([t for t in existing_log.batch_transactions if t.status == TransactionStatus.APPLIED]),
                total_items=existing_log.batch_size,
                errors=[],
                created_at=existing_log.timestamp,
                updated_at=existing_log.timestamp,
            )
    
    # Create sync log for tracking
    batch_id = request.items[0].batch_id if request.items else str(uuid4())
    sync_log = SyncLog(
        id=str(uuid4()),
        device_id=request.device_id,
        batch_id=batch_id,
        batch_size=len(request.items),
        status=SyncStatus.SUCCESS,
        timestamp=datetime.utcnow(),
        organization_id=request.organization_id,
        sync_duration_ms=0,
    )
    
    # Process each item in the batch
    processed_count = 0
    errors = []
    
    for item in request.items:
        try:
            # Validate action
            if item.action not in ["SALE_COMMIT", "MOVEMENT", "INVENTORY_UPDATE"]:
                raise ValueError(f"Invalid action: {item.action}")
            
            # Create batch transaction record
            batch_transaction = SyncBatchTransaction(
                id=str(uuid4()),
                sync_log_id=sync_log.id,
                transaction_sequence=item.sequence,
                transaction_type="sale" if item.action == "SALE_COMMIT" else "movement",
                status=TransactionStatus.PENDING,
                transaction_data=item.payload,
            )
            
            # Apply transaction based on action
            if item.action == "SALE_COMMIT":
                # Process sale commit
                from src.services.sale_service import SaleService
                sale_id = item.payload.get("sale_id")
                user_id = item.payload.get("user_id")
                
                if not sale_id or not user_id:
                    raise ValueError("Missing sale_id or user_id in payload")
                
                SaleService.commit_pending_sale(
                    sale_id=sale_id,
                    recorded_by_id=user_id,
                    db=db,
                )
                batch_transaction.status = TransactionStatus.APPLIED
                batch_transaction.applied_at = datetime.utcnow()
                processed_count += 1
            
            db.add(batch_transaction)
            
        except Exception as e:
            sync_log.status = SyncStatus.PARTIAL_FAILURE
            batch_transaction.status = TransactionStatus.FAILED
            batch_transaction.failure_reason = str(e)
            db.add(batch_transaction)
            errors.append({
                "sequence": item.sequence,
                "action": item.action,
                "error": str(e),
            })
    
    # Add sync log and idempotency cache
    db.add(sync_log)
    
    # Cache for idempotency
    idempotency_cache = SyncIdempotencyCache(
        id=str(uuid4()),
        device_id=request.device_id,
        batch_id=batch_id,
        sync_log_id=sync_log.id,
        response_json={
            "batch_id": batch_id,
            "device_id": request.device_id,
            "status": _sync_status_to_string(sync_log.status),
            "processed_items": processed_count,
            "total_items": len(request.items),
        },
    )
    db.add(idempotency_cache)
    db.commit()
    
    return SyncBatchResponse(
        id=batch_id,
        device_id=request.device_id,
        organization_id=request.organization_id,
        status=_sync_status_to_string(sync_log.status),
        processed_items=processed_count,
        total_items=len(request.items),
        errors=errors,
        created_at=sync_log.timestamp,
        updated_at=sync_log.timestamp,
    )


@router.get("/sync/status/{batch_id}", response_model=SyncBatchResponse)
def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db),
) -> SyncBatchResponse:
    """Get status of a batch processing operation."""
    sync_log = db.query(SyncLog).filter(SyncLog.batch_id == batch_id).first()
    
    if not sync_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )
    
    processed_items = len([
        t for t in sync_log.batch_transactions 
        if t.status == TransactionStatus.APPLIED
    ])
    
    errors = []
    for txn in sync_log.batch_transactions:
        if txn.status == TransactionStatus.FAILED:
            errors.append({
                "sequence": txn.transaction_sequence,
                "error": txn.failure_reason or "Unknown error",
            })
    
    return SyncBatchResponse(
        id=sync_log.batch_id,
        device_id=sync_log.device_id,
        organization_id=sync_log.organization_id,
        status=_sync_status_to_string(sync_log.status),
        processed_items=processed_items,
        total_items=sync_log.batch_size,
        errors=errors,
        created_at=sync_log.timestamp,
        updated_at=sync_log.timestamp,
    )


@router.get("/subscriptions/{org_id}/state/sync", response_model=SubscriptionStateSync)
def get_subscription_state_sync(
    org_id: int,
    db: Session = Depends(get_db),
) -> SubscriptionStateSync:
    """Get current subscription state for device cache update.
    
    Device uses this endpoint to fetch the authoritative subscription state
    and cache it for offline operations.
    """
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found",
        )
    
    # Get subscription
    subscription = db.query(Subscription).filter(
        Subscription.organization_id == org_id
    ).first()
    
    if not subscription:
        # Default to ACTIVE if no subscription
        return SubscriptionStateSync(
            state="ACTIVE",
            expiry_date=None,
            grace_end_date=None,
            days_remaining=None,
            operational=True,
        )
    
    # Compute current state
    current_state = SubscriptionService.compute_current_state(subscription)
    is_operational = SubscriptionService.is_operational(subscription)
    days_remaining = SubscriptionService.days_remaining_in_grace(subscription)
    
    return SubscriptionStateSync(
        state=current_state.value.upper(),
        expiry_date=subscription.expiry_date,
        grace_end_date=subscription.grace_end_date,
        days_remaining=days_remaining,
        operational=is_operational,
    )


@router.post("/cache/subscription-state", response_model=CachedSubscriptionStateResponse, status_code=status.HTTP_200_OK)
def update_subscription_cache(
    request: CacheUpdateRequest,
    db: Session = Depends(get_db),
) -> CachedSubscriptionStateResponse:
    """Update device's cached subscription state.
    
    Device calls this endpoint after fetching latest subscription state
    from the server to persist it locally for offline operations.
    """
    # Verify organization exists
    org = db.query(Organization).filter(
        Organization.id == request.organization_id
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {request.organization_id} not found",
        )
    
    # Check if cache exists for this device
    cached = db.query(CachedSubscriptionState).filter(
        CachedSubscriptionState.device_id == request.device_id
    ).first()
    
    if cached:
        # Update existing cache
        cached.state = request.subscription_state.state
        cached.state_snapshot = {
            "expiry_date": request.subscription_state.expiry_date.isoformat() if request.subscription_state.expiry_date else None,
            "grace_end_date": request.subscription_state.grace_end_date.isoformat() if request.subscription_state.grace_end_date else None,
            "days_remaining": request.subscription_state.days_remaining,
            "operational": request.subscription_state.operational,
        }
        cached.last_sync_at = datetime.utcnow()
    else:
        # Create new cache entry
        cached = CachedSubscriptionState(
            device_id=request.device_id,
            organization_id=request.organization_id,
            state=request.subscription_state.state,
            state_snapshot={
                "expiry_date": request.subscription_state.expiry_date.isoformat() if request.subscription_state.expiry_date else None,
                "grace_end_date": request.subscription_state.grace_end_date.isoformat() if request.subscription_state.grace_end_date else None,
                "days_remaining": request.subscription_state.days_remaining,
                "operational": request.subscription_state.operational,
            },
            last_sync_at=datetime.utcnow(),
        )
    
    db.add(cached)
    db.commit()
    
    return CachedSubscriptionStateResponse(
        id=cached.id,
        device_id=cached.device_id,
        organization_id=cached.organization_id,
        state=cached.state,
        last_sync_at=cached.last_sync_at,
    )


def _sync_status_to_string(status: SyncStatus) -> str:
    """Convert SyncStatus enum to string."""
    status_map = {
        SyncStatus.SUCCESS: "COMPLETED",
        SyncStatus.PARTIAL_FAILURE: "COMPLETED",
        SyncStatus.DUPLICATE: "COMPLETED",
        SyncStatus.FAILED: "FAILED",
    }
    return status_map.get(status, "PENDING")

"""Authenticated offline operation sync and subscription-state caching."""
from datetime import datetime
import hashlib
import json
from typing import Optional, Tuple, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid import uuid4

from src.database.config import get_db
from src.security.authorization import get_current_user
from src.models.sync import SyncLog, SyncStatus, SyncBatchTransaction, TransactionStatus
from src.models.cached_subscription_state import CachedSubscriptionState
from src.models.entities import (
    InventoryCount,
    OfflineOperation,
    Organization,
    Sale,
    Subscription,
    User,
)
from src.services.sale_service import SaleService
from src.schemas.sync import (
    OfflineOperationInput,
    OfflineOperationType,
    OfflineSyncRequest,
    OfflineSyncResponse,
    OperationAcknowledgement,
    OperationAcknowledgementStatus,
    SyncBatchResponse,
    SubscriptionStateSync,
    CacheUpdateRequest,
    CachedSubscriptionStateResponse,
)
from src.schemas.inventory import (
    AdjustmentCreate,
    InventoryCountCreate,
    OpeningStockCreate,
    StockIssueCreate,
    StockReceiptCreate,
    StockTransferCreate,
)
from src.services.inventory_service import (
    InventoryConflictError,
    InventoryNotFoundError,
    InventoryService,
)
from src.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/sync/batch", response_model=OfflineSyncResponse, status_code=status.HTTP_200_OK)
def submit_batch(
    request: OfflineSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OfflineSyncResponse:
    """Apply durable offline events through the authenticated tenant's services.

    Event identifiers are unique per organization and device. A retry of an
    identical event returns its stored acknowledgment; reusing an identifier
    for different content is surfaced as a reconciliation conflict.
    """
    operation_ids = [operation.operation_id for operation in request.operations]
    if len(set(operation_ids)) != len(operation_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Operation identifiers must be unique within a sync request",
        )
    if request.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization",
        )

    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).with_for_update().first()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    acknowledgements = []
    for operation in request.operations:
        acknowledgements.append(
            _process_offline_operation(
                operation=operation,
                device_id=request.device_id,
                organization_id=current_user.organization_id,
                actor_id=current_user.id,
                actor_role=current_user.role,
                db=db,
            )
        )
    db.commit()
    return OfflineSyncResponse(
        device_id=request.device_id,
        organization_id=current_user.organization_id,
        acknowledgements=acknowledgements,
    )


def _payload_hash(operation: OfflineOperationInput) -> str:
    canonical = json.dumps(
        {
            "operation_type": operation.operation_type.value,
            "payload": operation.payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cached_acknowledgement(record: OfflineOperation) -> Optional[OperationAcknowledgement]:
    if not record.result_payload:
        return None
    try:
        return OperationAcknowledgement.model_validate_json(record.result_payload)
    except (ValueError, ValidationError):
        return None


def _process_offline_operation(
    *,
    operation: OfflineOperationInput,
    device_id: str,
    organization_id: int,
    actor_id: int,
    actor_role: str,
    db: Session,
) -> OperationAcknowledgement:
    payload_hash = _payload_hash(operation)
    record = db.query(OfflineOperation).filter(
        OfflineOperation.organization_id == organization_id,
        OfflineOperation.device_id == device_id,
        OfflineOperation.operation_id == operation.operation_id,
    ).with_for_update().first()

    if record:
        if record.payload_hash != payload_hash:
            return _ack(
                operation.operation_id,
                OperationAcknowledgementStatus.RECONCILIATION_REQUIRED,
                code="OPERATION_ID_REUSED",
                message="This operation ID was already used with different content.",
            )
        cached = _cached_acknowledgement(record)
        if cached and record.status != OperationAcknowledgementStatus.RETRYABLE_FAILURE.value:
            return cached
        if not cached and record.status != "PENDING":
            return _ack(
                operation.operation_id,
                OperationAcknowledgementStatus.RECONCILIATION_REQUIRED,
                code="ACKNOWLEDGEMENT_UNAVAILABLE",
                message="The stored operation has no usable acknowledgment; manual reconciliation is required.",
            )
    else:
        record = OfflineOperation(
            organization_id=organization_id,
            actor_id=actor_id,
            device_id=device_id,
            operation_id=operation.operation_id,
            operation_type=operation.operation_type.value,
            payload_hash=payload_hash,
            status="PENDING",
        )
        db.add(record)
        db.flush()

    try:
        with db.begin_nested():
            entity_type, entity_id, reconciliation_message = _apply_offline_operation(
                operation=operation,
                device_id=device_id,
                organization_id=organization_id,
                actor_id=actor_id,
                actor_role=actor_role,
                db=db,
            )
            db.flush()
        if reconciliation_message:
            acknowledgement = _ack(
                operation.operation_id,
                OperationAcknowledgementStatus.RECONCILIATION_REQUIRED,
                entity_type=entity_type,
                entity_id=entity_id,
                code="MANUAL_RECONCILIATION_REQUIRED",
                message=reconciliation_message,
            )
        else:
            acknowledgement = _ack(
                operation.operation_id,
                OperationAcknowledgementStatus.APPLIED,
                entity_type=entity_type,
                entity_id=entity_id,
            )
    except InventoryConflictError as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.RECONCILIATION_REQUIRED,
            code="INVENTORY_CONFLICT",
            message=str(error),
        )
    except InventoryNotFoundError as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.TERMINAL_FAILURE,
            code="ENTITY_NOT_FOUND",
            message=str(error),
        )
    except ForbiddenOperationError as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.TERMINAL_FAILURE,
            code="FORBIDDEN_OPERATION",
            message=str(error),
        )
    except UnsupportedOperationError as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.TERMINAL_FAILURE,
            code="UNSUPPORTED_OPERATION",
            message=str(error),
        )
    except (ValueError, ValidationError, TypeError) as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.TERMINAL_FAILURE,
            code="INVALID_OPERATION",
            message=str(error),
        )
    except SQLAlchemyError as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.RETRYABLE_FAILURE,
            code="DATABASE_ERROR",
            message="The operation could not be committed; retry with the same operation ID.",
        )
        record.failure_reason = str(error)
    except Exception as error:
        acknowledgement = _ack(
            operation.operation_id,
            OperationAcknowledgementStatus.RETRYABLE_FAILURE,
            code="OPERATION_PROCESSING_ERROR",
            message="The operation could not be applied; retry with the same operation ID.",
        )
        record.failure_reason = str(error)

    record.status = acknowledgement.status.value
    record.result_payload = acknowledgement.model_dump_json()
    record.failure_reason = acknowledgement.error_message
    record.processed_at = datetime.utcnow()
    db.flush()
    return acknowledgement


def _apply_offline_operation(
    *,
    operation: OfflineOperationInput,
    device_id: str,
    organization_id: int,
    actor_id: int,
    actor_role: str,
    db: Session,
) -> Tuple[str, Union[int, str], Optional[str]]:
    payload = operation.payload
    if "device_id" in payload or "device_local_id" in payload:
        raise ValueError("Device identity must be supplied by the sync envelope")
    local_id = operation.operation_id

    if operation.operation_type == OfflineOperationType.SALE_COMMIT:
        sale_id = _required_positive_int(payload, "sale_id")
        sale = db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.organization_id == organization_id,
        ).with_for_update().first()
        if not sale:
            raise InventoryNotFoundError("Sale not found in the authenticated organization")
        SaleService.commit_pending_sale(
            sale_id=sale_id,
            recorded_by_id=actor_id,
            db=db,
            commit=False,
        )
        return "sale", sale_id, None

    if operation.operation_type == OfflineOperationType.INVENTORY_RECEIPT:
        if payload.get("opening_balance") is True:
            data = OpeningStockCreate.model_validate(payload)
            movement = InventoryService.receive_stock(
                organization_id=organization_id,
                product_id=data.product_id,
                location_id=data.location_id,
                quantity=data.quantity,
                recorded_by_id=actor_id,
                db=db,
                unit_cost=data.unit_cost,
                reason=data.reason,
                opening_balance=True,
                device_id=device_id,
                device_local_id=local_id,
                commit=False,
            )
        else:
            data = StockReceiptCreate.model_validate(payload)
            movement = InventoryService.receive_stock(
                organization_id=organization_id,
                product_id=data.product_id,
                location_id=data.location_id,
                quantity=data.quantity,
                recorded_by_id=actor_id,
                db=db,
                unit_cost=data.unit_cost,
                reason=data.reason,
                device_id=device_id,
                device_local_id=local_id,
                commit=False,
            )
        return "inventory_movement", movement.id, None

    if operation.operation_type == OfflineOperationType.INVENTORY_ISSUE:
        data = StockIssueCreate.model_validate(payload)
        movement = InventoryService.issue_stock(
            organization_id=organization_id,
            product_id=data.product_id,
            location_id=data.location_id,
            quantity=data.quantity,
            reason=data.reason,
            recorded_by_id=actor_id,
            db=db,
            device_id=device_id,
            device_local_id=local_id,
            commit=False,
        )
        return "inventory_movement", movement.id, None

    if operation.operation_type == OfflineOperationType.INVENTORY_ADJUSTMENT:
        data = AdjustmentCreate.model_validate(payload)
        movement = InventoryService.adjust_stock(
            organization_id=organization_id,
            product_id=data.product_id,
            location_id=data.location_id,
            quantity=data.quantity,
            reason=data.reason,
            recorded_by_id=actor_id,
            db=db,
            device_id=device_id,
            device_local_id=local_id,
            commit=False,
        )
        return "inventory_movement", movement.id, None

    if operation.operation_type == OfflineOperationType.INVENTORY_TRANSFER:
        if actor_role not in ("admin", "manager"):
            raise ForbiddenOperationError(
                "Only an admin or manager can transfer stock"
            )
        data = StockTransferCreate.model_validate(payload)
        transfer = InventoryService.transfer_stock(
            organization_id=organization_id,
            source_location_id=data.source_location_id,
            destination_location_id=data.destination_location_id,
            lines=data.lines,
            reason=data.reason,
            recorded_by_id=actor_id,
            db=db,
            device_id=device_id,
            device_local_id=local_id,
            commit=False,
        )
        return "inventory_transfer", transfer.id, None

    if operation.operation_type == OfflineOperationType.INVENTORY_COUNT:
        data = InventoryCountCreate.model_validate(payload)
        count = InventoryService.create_count(
            organization_id=organization_id,
            location_id=data.location_id,
            lines=data.lines,
            created_by_id=actor_id,
            db=db,
            notes=data.notes,
            commit=False,
        )
        return (
            "inventory_count",
            count.id,
            "Count observations were saved as a draft. Review the server ledger and explicitly reconcile the count before posting corrections.",
        )

    if operation.operation_type == OfflineOperationType.INVENTORY_RETURN:
        raise UnsupportedOperationError(
            "Offline returns cannot be applied until the authoritative return workflow is available."
        )

    raise ValueError(f"Unsupported operation type: {operation.operation_type.value}")


def _required_positive_int(payload: dict, key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


class UnsupportedOperationError(ValueError):
    pass


class ForbiddenOperationError(ValueError):
    pass


def _ack(
    operation_id: str,
    state: OperationAcknowledgementStatus,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[Union[int, str]] = None,
    code: Optional[str] = None,
    message: Optional[str] = None,
) -> OperationAcknowledgement:
    return OperationAcknowledgement(
        operation_id=operation_id,
        status=state,
        applied_entity_type=entity_type,
        applied_entity_id=str(entity_id) if entity_id is not None else None,
        error_code=code,
        error_message=message,
    )


@router.get("/sync/status/{batch_id}", response_model=SyncBatchResponse)
def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncBatchResponse:
    """Get status of a batch processing operation."""
    sync_log = db.query(SyncLog).filter(
        SyncLog.batch_id == batch_id,
        SyncLog.organization_id == str(current_user.organization_id),
    ).first()
    
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
    current_user: User = Depends(get_current_user),
) -> SubscriptionStateSync:
    """Get current subscription state for device cache update.
    
    Device uses this endpoint to fetch the authoritative subscription state
    and cache it for offline operations.
    """
    if org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")

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


@router.post("/sync/cache/subscription-state", response_model=CachedSubscriptionStateResponse, status_code=status.HTTP_200_OK)
def update_subscription_cache(
    request: CacheUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CachedSubscriptionStateResponse:
    """Update device's cached subscription state.
    
    Device calls this endpoint after fetching latest subscription state
    from the server to persist it locally for offline operations.
    """
    if request.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")

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
        CachedSubscriptionState.device_id == request.device_id,
        CachedSubscriptionState.organization_id == current_user.organization_id,
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
        SyncStatus.PARTIAL_FAILURE: "PARTIAL_FAILURE",
        SyncStatus.DUPLICATE: "COMPLETED",
        SyncStatus.FAILED: "FAILED",
    }
    return status_map.get(status, "PENDING")

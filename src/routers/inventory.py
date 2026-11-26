"""Inventory API router for stock queries and adjustments.

This module provides endpoints for managing inventory and stock levels.
Operations include:
- Query current stock levels at locations
- Record inventory movements (receipts, issues, transfers)
- Perform manual stock adjustments
- View inventory discrepancies

Supports tracking of physical counts vs system ledger for reconciliation.
Handles reasons for adjustments (damage, shrinkage, physical count discrepancies, etc.)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from decimal import Decimal
from typing import Optional

from src.database.config import get_db
from src.security.authorization import get_current_user
from src.models.entities import (
    InventoryMovement,
    InventoryCount,
    InventoryCountLine,
    InventoryTransfer,
    InventoryTransferLine,
    Organization,
    Product,
    Location,
    User,
)
from src.services.inventory_service import (
    InventoryConflictError,
    InventoryNotFoundError,
    InventoryService,
)
from src.services.adjustment_reasons import validate_and_normalize_reason
from src.schemas.inventory import (
    StockResponse,
    StockItem,
    InventoryMovement as InventoryMovementSchema,
    MovementListResponse,
    MovementDetailResponse,
    AdjustmentCreate,
    Discrepancy,
    DiscrepancyListResponse,
    InventoryCountCreate,
    InventoryCountObservationUpdate,
    InventoryCountReconcileRequest,
    InventoryCountResponse,
    InventoryCountLineResponse,
    InventoryValueItem,
    InventoryValueReport,
    LocationInventoryItem,
    LocationInventoryReport,
    LowStockItem,
    LowStockReport,
    OpeningStockCreate,
    StockIssueCreate,
    StockReceiptCreate,
    StockTransferCreate,
    InventoryTransferResponse,
    InventoryTransferLineResponse,
)

router = APIRouter()


def _raise_inventory_error(error: Exception) -> None:
    if isinstance(error, InventoryNotFoundError):
        raise HTTPException(status_code=404, detail=str(error))
    if isinstance(error, InventoryConflictError):
        raise HTTPException(status_code=409, detail=str(error))
    if isinstance(error, ValueError):
        raise HTTPException(status_code=422, detail=str(error))
    raise error


def _count_response(count: InventoryCount, organization_id: int, db: Session):
    lines = db.query(InventoryCountLine).filter(
        InventoryCountLine.count_id == count.id
    ).order_by(InventoryCountLine.id).all()
    result_lines = []
    for line in lines:
        product = db.query(Product).filter(
            Product.id == line.product_id,
            Product.organization_id == organization_id,
        ).first()
        result_lines.append(
            InventoryCountLineResponse(
                id=line.id,
                product_id=line.product_id,
                product_name=product.name if product else "Unknown",
                expected_quantity=line.expected_quantity,
                observed_quantity=line.observed_quantity,
                difference=(
                    line.observed_quantity - line.expected_quantity
                    if line.observed_quantity is not None
                    else None
                ),
                reconciled_movement_id=line.reconciled_movement_id,
            )
        )
    return InventoryCountResponse(
        id=count.id,
        location_id=count.location_id,
        status=count.status,
        notes=count.notes,
        created_by_id=count.created_by_id,
        reconciled_by_id=count.reconciled_by_id,
        started_at=count.started_at,
        reconciled_at=count.reconciled_at,
        lines=result_lines,
    )


def _transfer_response(transfer: InventoryTransfer, db: Session):
    lines = db.query(InventoryTransferLine).filter(
        InventoryTransferLine.transfer_id == transfer.id
    ).order_by(InventoryTransferLine.product_id).all()
    return InventoryTransferResponse(
        id=transfer.id,
        source_location_id=transfer.source_location_id,
        destination_location_id=transfer.destination_location_id,
        reason=transfer.reason,
        status=transfer.status,
        created_by_id=transfer.created_by_id,
        device_id=transfer.device_id,
        device_local_id=transfer.device_local_id,
        created_at=transfer.created_at,
        lines=[
            InventoryTransferLineResponse(
                product_id=line.product_id,
                quantity=line.quantity,
            )
            for line in lines
        ],
    )


@router.get(
    "/locations/{location_id}/stock",
    response_model=StockResponse,
    tags=["Inventory"]
)
def get_stock_at_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current stock for all products at a location.
    
    SECURITY: organization_id is derived from current_user, not client request.
    
    Args:
        location_id: Location ID
        db: Database session
        current_user: Authenticated user (provides organization context)
        
    Returns:
        StockResponse with list of products and quantities
        
    Raises:
        403: User does not have access to this location
        404: Location not found
    """
    # Verify location exists and belongs to user's organization
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.organization_id == current_user.organization_id,
    ).first()
    if not location:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this location or location not found",
        )
    
    # Get all products for this organization (derived from authenticated user)
    products = db.query(Product).filter(
        Product.organization_id == current_user.organization_id,
        Product.is_active == True,
    ).all()
    balances = InventoryService.get_balances_at_location(
        current_user.organization_id, location_id, db
    )
    last_movements = {}
    for movement in db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == current_user.organization_id,
        (
            (InventoryMovement.location_id == location_id)
            | (InventoryMovement.to_location_id == location_id)
        ),
    ).order_by(
        desc(InventoryMovement.created_at),
        desc(InventoryMovement.id),
    ).all():
        last_movements.setdefault(movement.product_id, movement)

    items = []
    for product in products:
        quantity = balances.get(product.id, 0)
        last_movement = last_movements.get(product.id)
        
        items.append(StockItem(
            product_id=product.id,
            product_name=product.name,
            quantity=quantity,
            last_movement_date=last_movement.created_at if last_movement else None,
        ))
    
    return StockResponse(
        location_id=location_id,
        items=items,
        total_items=len(items),
    )


@router.get(
    "/stock/movements",
    response_model=MovementListResponse,
    tags=["Inventory"]
)
def list_movements(
    product_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of inventory movements.
    
    SECURITY: organization_id is derived from current_user, not client request.
    
    Args:
        product_id: Optional filter by product
        location_id: Optional filter by location
        skip: Number of records to skip (pagination)
        limit: Number of records to return (default 20, max 100)
        db: Database session
        current_user: Authenticated user (provides organization context)
        
    Returns:
        MovementListResponse with paginated movements
    """
    query = db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == current_user.organization_id
    )
    
    if product_id is not None:
        if not db.query(Product.id).filter(
            Product.id == product_id,
            Product.organization_id == current_user.organization_id,
        ).first():
            raise HTTPException(status_code=404, detail="Product not found")
        query = query.filter(InventoryMovement.product_id == product_id)
    
    if location_id is not None:
        if not db.query(Location.id).filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        ).first():
            raise HTTPException(status_code=404, detail="Location not found")
        query = query.filter(
            (InventoryMovement.location_id == location_id)
            | (InventoryMovement.to_location_id == location_id)
        )
    
    total = query.count()
    items = query.order_by(desc(InventoryMovement.created_at)).offset(skip).limit(limit).all()
    
    return MovementListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stock/movements/{movement_id}",
    response_model=MovementDetailResponse,
    tags=["Inventory"]
)
def get_movement_detail(
    movement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information for a specific inventory movement.
    
    SECURITY: organization_id is derived from current_user, not client request.
    
    Args:
        movement_id: Movement ID
        db: Database session
        current_user: Authenticated user (provides organization context)
        
    Returns:
        MovementDetailResponse with full movement details including product and user names
        
    Raises:
        403: Access denied to this movement
        404: Movement not found
    """
    movement = db.query(InventoryMovement).filter(
        InventoryMovement.id == movement_id,
        InventoryMovement.organization_id == current_user.organization_id,
    ).first()
    
    if not movement:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this movement or movement not found",
        )
    
    product = db.query(Product).filter(
        Product.id == movement.product_id,
        Product.organization_id == current_user.organization_id,
    ).first()
    product_name = product.name if product else "Unknown"
    user = db.query(User).filter(
        User.id == movement.recorded_by_id,
        User.organization_id == current_user.organization_id,
    ).first()
    user_name = user.full_name if user else "Unknown"
    
    return MovementDetailResponse(
        id=movement.id,
        product_id=movement.product_id,
        product_name=product_name,
        location_id=movement.location_id,
        quantity=movement.quantity,
        reason=movement.reason,
        recorded_by_id=movement.recorded_by_id,
        user_name=user_name,
        created_at=movement.created_at,
    )


@router.post(
    "/stock/adjust",
    response_model=InventoryMovementSchema,
    status_code=201,
    tags=["Inventory"]
)
def create_adjustment(
    adjustment: AdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a manual inventory adjustment.
    
    CRITICAL: recorded_by_id is derived from JWT token (current_user), not client request.
    organization_id is derived from authenticated user's organization, not client param.
    Reason may be provided as user-friendly label or canonical code; it is normalized to canonical.
    
    Args:
        adjustment: Adjustment data (product_id, location_id, quantity, reason, note)
                   - reason: Can be a user-friendly label (e.g., "Physical Count") or 
                            canonical code (e.g., "PHYSICAL_COUNT_DISCREPANCY")
        db: Database session
        current_user: Authenticated user (provides identity and organization context)
        
    Returns:
        Created InventoryMovement record with canonical reason code
        
    Raises:
        401: If not authenticated
        403: If location not in user's organization
        404: Product or location not found
        400: Invalid reason (unknown label or code)
    """
    # Validate and normalize reason: accepts both labels and canonical codes
    try:
        canonical_reason = validate_and_normalize_reason(adjustment.reason)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid adjustment reason: {str(e)}"
        )
    
    # SECURITY: Verify location belongs to user's organization before allowing adjustment
    location = db.query(Location).filter(
        Location.id == adjustment.location_id,
        Location.organization_id == current_user.organization_id,
    ).first()
    if not location:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this location or location not found",
        )
    
    try:
        # SECURITY: Use current_user.id as the authoritative recorded_by_id, not from request
        # Use canonical_reason (normalized from user input) to persist consistent audit trail
        movement = InventoryService.adjust_stock(
            organization_id=current_user.organization_id,  # SECURITY: From token, not request
            product_id=adjustment.product_id,
            location_id=adjustment.location_id,
            quantity=adjustment.quantity,
            reason=canonical_reason,  # Use normalized canonical code, not raw input
            recorded_by_id=current_user.id,  # SECURITY: From JWT token, not request body
            db=db,
        )
        return movement
    except ValueError as e:
        db.rollback()
        if isinstance(e, InventoryNotFoundError):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid adjustment: {str(e)}")
    except InventoryConflictError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        db.rollback()
        raise


@router.post(
    "/stock/receive",
    response_model=InventoryMovementSchema,
    status_code=201,
    tags=["Inventory"],
)
def receive_stock(
    request: StockReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return InventoryService.receive_stock(
            organization_id=current_user.organization_id,
            product_id=request.product_id,
            location_id=request.location_id,
            quantity=request.quantity,
            recorded_by_id=current_user.id,
            db=db,
            unit_cost=request.unit_cost,
            reason=request.reason,
            device_id=request.device_id,
            device_local_id=request.device_local_id,
        )
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.post(
    "/stock/opening",
    response_model=InventoryMovementSchema,
    status_code=201,
    tags=["Inventory"],
)
def record_opening_stock(
    request: OpeningStockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return InventoryService.receive_stock(
            organization_id=current_user.organization_id,
            product_id=request.product_id,
            location_id=request.location_id,
            quantity=request.quantity,
            recorded_by_id=current_user.id,
            db=db,
            unit_cost=request.unit_cost,
            reason=request.reason,
            opening_balance=True,
            device_id=request.device_id,
            device_local_id=request.device_local_id,
        )
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.post(
    "/stock/issue",
    response_model=InventoryMovementSchema,
    status_code=201,
    tags=["Inventory"],
)
def issue_stock(
    request: StockIssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return InventoryService.issue_stock(
            organization_id=current_user.organization_id,
            product_id=request.product_id,
            location_id=request.location_id,
            quantity=request.quantity,
            reason=request.reason,
            recorded_by_id=current_user.id,
            db=db,
            device_id=request.device_id,
            device_local_id=request.device_local_id,
        )
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.post(
    "/stock/transfer",
    response_model=InventoryTransferResponse,
    status_code=201,
    tags=["Inventory"],
)
def transfer_stock(
    request: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only an admin or manager can transfer stock")
    try:
        transfer = InventoryService.transfer_stock(
            organization_id=current_user.organization_id,
            source_location_id=request.source_location_id,
            destination_location_id=request.destination_location_id,
            lines=request.lines,
            reason=request.reason,
            recorded_by_id=current_user.id,
            db=db,
            device_id=request.device_id,
            device_local_id=request.device_local_id,
        )
        return _transfer_response(transfer, db)
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.post(
    "/stock/counts",
    response_model=InventoryCountResponse,
    status_code=201,
    tags=["Inventory"],
)
def create_inventory_count(
    request: InventoryCountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        count = InventoryService.create_count(
            organization_id=current_user.organization_id,
            location_id=request.location_id,
            lines=request.lines,
            created_by_id=current_user.id,
            db=db,
            notes=request.notes,
        )
        return _count_response(count, current_user.organization_id, db)
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/stock/counts/{count_id}",
    response_model=InventoryCountResponse,
    tags=["Inventory"],
)
def update_inventory_count(
    count_id: int,
    request: InventoryCountObservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        count = InventoryService.update_count_observations(
            organization_id=current_user.organization_id,
            count_id=count_id,
            lines=request.lines,
            db=db,
        )
        return _count_response(count, current_user.organization_id, db)
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.get(
    "/stock/counts/{count_id}",
    response_model=InventoryCountResponse,
    tags=["Inventory"],
)
def get_inventory_count(
    count_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(InventoryCount).filter(
        InventoryCount.id == count_id,
        InventoryCount.organization_id == current_user.organization_id,
    ).first()
    if not count:
        raise HTTPException(status_code=404, detail="Count not found")
    return _count_response(count, current_user.organization_id, db)


@router.post(
    "/stock/counts/{count_id}/reconcile",
    response_model=InventoryCountResponse,
    tags=["Inventory"],
)
def reconcile_inventory_count(
    count_id: int,
    request: InventoryCountReconcileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only an admin or manager can reconcile inventory counts",
        )
    try:
        count = InventoryService.reconcile_count(
            organization_id=current_user.organization_id,
            count_id=count_id,
            reconciled_by_id=current_user.id,
            expected_observations=request.expected_observations,
            db=db,
        )
        return _count_response(count, current_user.organization_id, db)
    except (InventoryNotFoundError, InventoryConflictError, ValueError) as error:
        db.rollback()
        _raise_inventory_error(error)
    except Exception:
        db.rollback()
        raise


@router.get(
    "/stock/valuation",
    response_model=InventoryValueReport,
    tags=["Inventory"],
)
def get_inventory_valuation(
    location_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    locations_query = db.query(Location).filter(
        Location.organization_id == current_user.organization_id,
        Location.is_active.is_(True),
    )
    if location_id is not None:
        locations_query = locations_query.filter(Location.id == location_id)
        if not locations_query.first():
            raise HTTPException(status_code=404, detail="Location not found")
    locations = locations_query.order_by(Location.id).all()
    products = db.query(Product).filter(
        Product.organization_id == current_user.organization_id,
        Product.is_active.is_(True),
    ).order_by(Product.id).all()
    average_costs = {
        product.id: InventoryService.weighted_average_cost(
            current_user.organization_id, product.id, db
        )
        for product in products
    }
    rows = []
    known_values = []
    valuation_complete = True
    for location in locations:
        balances = InventoryService.get_balances_at_location(
            current_user.organization_id, location.id, db
        )
        for product in products:
            quantity = balances.get(product.id, 0)
            average_cost = average_costs[product.id]
            value = (
                (Decimal(quantity) * average_cost).quantize(Decimal("0.01"))
                if average_cost is not None
                else None
            )
            if quantity != 0 and average_cost is None:
                valuation_complete = False
            if value is not None:
                known_values.append(value)
            rows.append(
                InventoryValueItem(
                    product_id=product.id,
                    product_name=product.name,
                    location_id=location.id,
                    quantity=quantity,
                    weighted_average_cost=average_cost,
                    inventory_value=value,
                    currency_code=organization.currency_code,
                )
            )
    return InventoryValueReport(
        items=rows,
        currency_code=organization.currency_code,
        total_value=(
            sum(known_values, Decimal("0.00"))
            if organization.currency_code and valuation_complete
            else None
        ),
        valuation_complete=valuation_complete,
    )


@router.get(
    "/stock/low-stock",
    response_model=LowStockReport,
    tags=["Inventory"],
)
def get_low_stock(
    location_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    locations_query = db.query(Location).filter(
        Location.organization_id == current_user.organization_id,
        Location.is_active.is_(True),
    )
    if location_id is not None:
        locations_query = locations_query.filter(Location.id == location_id)
        if not locations_query.first():
            raise HTTPException(status_code=404, detail="Location not found")
    products = db.query(Product).filter(
        Product.organization_id == current_user.organization_id,
        Product.is_active.is_(True),
    ).order_by(Product.id).all()
    rows = []
    for location in locations_query.order_by(Location.id).all():
        balances = InventoryService.get_balances_at_location(
            current_user.organization_id, location.id, db
        )
        for product in products:
            quantity = balances.get(product.id, 0)
            minimum = product.minimum_stock_level or 0
            if quantity <= minimum:
                rows.append(
                    LowStockItem(
                        product_id=product.id,
                        product_name=product.name,
                        location_id=location.id,
                        quantity=quantity,
                        minimum_stock_level=minimum,
                    )
                )
    return LowStockReport(items=rows, total_items=len(rows))


@router.get(
    "/locations/{location_id}/report",
    response_model=LocationInventoryReport,
    tags=["Inventory"],
)
def get_location_inventory_report(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.organization_id == current_user.organization_id,
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    products = db.query(Product).filter(
        Product.organization_id == current_user.organization_id,
        Product.is_active.is_(True),
    ).order_by(Product.id).all()
    balances = InventoryService.get_balances_at_location(
        current_user.organization_id, location_id, db
    )
    rows = []
    values = []
    valuation_complete = True
    for product in products:
        quantity = balances.get(product.id, 0)
        average_cost = InventoryService.weighted_average_cost(
            current_user.organization_id, product.id, db
        )
        value = (
            (Decimal(quantity) * average_cost).quantize(Decimal("0.01"))
            if average_cost is not None
            else None
        )
        if quantity != 0 and average_cost is None:
            valuation_complete = False
        if value is not None:
            values.append(value)
        rows.append(
            LocationInventoryItem(
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                weighted_average_cost=average_cost,
                inventory_value=value,
                currency_code=organization.currency_code if organization else None,
            )
        )
    return LocationInventoryReport(
        location_id=location_id,
        items=rows,
        total_items=len(rows),
        currency_code=organization.currency_code if organization else None,
        total_value=(
            sum(values, Decimal("0.00"))
            if organization and organization.currency_code and valuation_complete
            else None
        ),
        valuation_complete=valuation_complete,
    )


@router.get(
    "/stock/discrepancies",
    response_model=DiscrepancyListResponse,
    tags=["Inventory"]
)
def list_discrepancies(
    location_id: int = Query(..., gt=0),
    organization_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of inventory discrepancies at a location.
    
    This endpoint compares physical counts (if recorded) with ledger quantities.
    Discrepancy is calculated as: physical_count - ledger_count
    
    Args:
        location_id: Location ID (required query parameter)
        organization_id: Organization ID (required query parameter)
        db: Database session
        
    Returns:
        DiscrepancyListResponse with list of discrepancies at location
        
    Raises:
        404: Location not found
    """
    if organization_id is not None and organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this organization")
    organization_id = current_user.organization_id

    # Verify location exists
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.organization_id == organization_id,
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    count_rows = db.query(InventoryCountLine, InventoryCount.started_at).join(
        InventoryCount,
        InventoryCount.id == InventoryCountLine.count_id,
    ).filter(
        InventoryCount.organization_id == organization_id,
        InventoryCount.location_id == location_id,
        InventoryCount.status == "DRAFT",
        InventoryCountLine.observed_quantity.is_not(None),
    ).order_by(InventoryCount.started_at.desc(), InventoryCountLine.id.desc()).all()
    latest_observations = {}
    for line, _started_at in count_rows:
        latest_observations.setdefault(line.product_id, line.observed_quantity)

    # Compare recorded physical observations with the authoritative ledger.
    products = db.query(Product).filter(
        Product.organization_id == organization_id,
        Product.is_active == True,
    ).all()
    
    discrepancies = []
    for product in products:
        # Compute ledger count from movements
        ledger_count = InventoryService.compute_stock_at_location(
            organization_id=organization_id,
            product_id=product.id,
            location_id=location_id,
            db=db,
        )
        
        physical_count = latest_observations.get(product.id)
        if physical_count is None:
            continue
        discrepancy = physical_count - ledger_count
        if discrepancy != 0:
            discrepancies.append(Discrepancy(
                product_id=product.id,
                location_id=location_id,
                physical_count=physical_count,
                ledger_count=ledger_count,
                discrepancy=discrepancy,
            ))
    
    return DiscrepancyListResponse(
        items=discrepancies,
        location_id=location_id,
    )

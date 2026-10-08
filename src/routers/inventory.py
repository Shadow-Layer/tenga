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
from datetime import datetime
from typing import Optional

from src.database.config import get_db
from src.security.authorization import get_current_user
from src.models.entities import (
    InventoryMovement,
    Product,
    Location,
    Stock,
    Organization,
    User,
)
from src.services.inventory_service import InventoryService
from src.schemas.inventory import (
    StockResponse,
    StockItem,
    InventoryMovement as InventoryMovementSchema,
    MovementListResponse,
    MovementDetailResponse,
    AdjustmentCreate,
    Discrepancy,
    DiscrepancyListResponse,
)

router = APIRouter()


@router.get(
    "/locations/{location_id}/stock",
    response_model=StockResponse,
    tags=["Inventory"]
)
def get_stock_at_location(
    location_id: int,
    organization_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Get current stock for all products at a location.
    
    Args:
        location_id: Location ID
        organization_id: Organization ID (required query parameter)
        db: Database session
        
    Returns:
        StockResponse with list of products and quantities
        
    Raises:
        404: Location not found
    """
    # Verify location exists
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.organization_id == organization_id,
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get all products for this organization
    products = db.query(Product).filter(
        Product.organization_id == organization_id,
        Product.is_active == True,
    ).all()
    
    items = []
    for product in products:
        # Compute stock for this product at this location
        quantity = InventoryService.compute_stock_at_location(
            organization_id=organization_id,
            product_id=product.id,
            location_id=location_id,
            db=db,
        )
        
        # Get last movement date for this product at this location
        last_movement = db.query(InventoryMovement).filter(
            InventoryMovement.organization_id == organization_id,
            InventoryMovement.product_id == product.id,
            InventoryMovement.location_id == location_id,
        ).order_by(desc(InventoryMovement.created_at)).first()
        
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
    organization_id: int = Query(..., gt=0),
    product_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get paginated list of inventory movements.
    
    Args:
        organization_id: Organization ID (required query parameter)
        product_id: Optional filter by product
        location_id: Optional filter by location
        skip: Number of records to skip (pagination)
        limit: Number of records to return (default 20, max 100)
        db: Database session
        
    Returns:
        MovementListResponse with paginated movements
    """
    query = db.query(InventoryMovement).filter(
        InventoryMovement.organization_id == organization_id
    )
    
    if product_id is not None:
        query = query.filter(InventoryMovement.product_id == product_id)
    
    if location_id is not None:
        query = query.filter(InventoryMovement.location_id == location_id)
    
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
    organization_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Get detailed information for a specific inventory movement.
    
    Args:
        movement_id: Movement ID
        organization_id: Organization ID (required query parameter)
        db: Database session
        
    Returns:
        MovementDetailResponse with full movement details including product and user names
        
    Raises:
        404: Movement not found
    """
    movement = db.query(InventoryMovement).filter(
        InventoryMovement.id == movement_id,
        InventoryMovement.organization_id == organization_id,
    ).first()
    
    if not movement:
        raise HTTPException(status_code=404, detail="Movement not found")
    
    # Get product name
    product = db.query(Product).filter(Product.id == movement.product_id).first()
    product_name = product.name if product else "Unknown"
    
    # Get user name
    user = db.query(User).filter(User.id == movement.recorded_by_id).first()
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
    organization_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    """Record a manual inventory adjustment.
    
    Args:
        adjustment: Adjustment data
        organization_id: Organization ID (required query parameter)
        db: Database session
        
    Returns:
        Created InventoryMovement record
        
    Raises:
        404: Product or location not found
        422: Invalid reason
    """
    # Validate reason
    valid_reasons = ["PHYSICAL_COUNT_DISCREPANCY", "DAMAGE", "SHRINKAGE", "ADJUSTMENT"]
    if adjustment.reason not in valid_reasons:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"
        )
    
    try:
        movement = InventoryService.record_movement(
            organization_id=organization_id,
            product_id=adjustment.product_id,
            location_id=adjustment.location_id,
            quantity=adjustment.quantity,
            reason=adjustment.reason,
            recorded_by_id=adjustment.recorded_by_id,
            reference_type="ADJUSTMENT",
            reference_id=None,
            db=db,
        )
        return movement
    except ValueError as e:
        # Service raises ValueError for missing product/location
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/stock/discrepancies",
    response_model=DiscrepancyListResponse,
    tags=["Inventory"]
)
def list_discrepancies(
    location_id: int = Query(..., gt=0),
    organization_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
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
    # Verify location exists
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.organization_id == organization_id,
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get all products for this organization
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
        
        # Get physical count from Stock table (most recent)
        stock = db.query(Stock).filter(
            Stock.organization_id == organization_id,
            Stock.product_id == product.id,
            Stock.location_id == location_id,
        ).first()
        
        physical_count = stock.quantity if stock else 0
        
        # Only include if there's a discrepancy
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

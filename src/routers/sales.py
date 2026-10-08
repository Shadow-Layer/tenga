"""Sales router for POS transactions.

This module provides endpoints for managing Point-of-Sale transactions.
Operations include:
- Create sales (can be online or offline/pending)
- Retrieve sale details and sales history
- Commit pending sales to the system
- Query sales by till or cashier

Sales can be created as:
- COMPLETED: Immediately committed online sales
- PENDING: Offline sales that need to be synced later

Supports multiple payment methods:
- CASH
- CARD
- MOBILE
- Other custom payment methods

Note: Stock oversell is allowed per design (U006).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.services.sale_service import SaleService
from src.models.entities import Sale, Till, User
from src.schemas.sale import (
    SaleCreate,
    SaleResponse,
    SaleListResponse,
    SaleCommitRequest,
    SaleCommitResponse,
    SaleItemResponse,
)
from src.security.authorization import get_current_user

router = APIRouter()


@router.post("/sales", response_model=SaleResponse, status_code=201)
def create_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new sale (online or offline).

    - **till_id**: Till where sale is made
    - **cashier_id**: User ID of cashier
    - **payment_method**: Payment method
    - **items**: List of items with product_id, quantity, unit_price
    - **is_offline**: If true, sale is queued as PENDING (offline)
    - Returns: 201 Created with Sale object
    - Error: 404 if till not found, 422 if invalid items

    Note: Oversell is allowed (no stock validation per U006)
    """
    try:
        # Validate till exists and belongs to user's organization
        till = db.query(Till).filter(
            Till.id == sale_data.till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        if not till:
            raise HTTPException(
                status_code=404,
                detail=f"Till {sale_data.till_id} not found",
            )

        # Convert items to service format
        items = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in sale_data.items
        ]

        # Create sale
        sale = SaleService.create_sale(
            organization_id=till.organization_id,
            till_id=sale_data.till_id,
            cashier_id=sale_data.cashier_id,
            payment_method=sale_data.payment_method,
            items=items,
            offline_device_id="OFFLINE" if sale_data.is_offline else None,
            notes=sale_data.notes,
            db=db,
        )

        return SaleResponse.from_orm(sale)

    except ValueError as e:
        # Handle validation errors from service
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=422, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/sales", response_model=SaleListResponse)
def list_sales(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    till_id: int = Query(None, description="Optional filter by till ID"),
    status: str = Query(None, description="Optional filter by status (PENDING, COMPLETED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List sales with optional filtering.

    - **skip**: Pagination offset
    - **limit**: Pagination limit
    - **till_id**: Optional filter by till
    - **status**: Optional filter by status
    - Returns: 200 with paginated list of sales
    """
    query = db.query(Sale).filter(Sale.organization_id == current_user.organization_id)

    # Apply filters
    if till_id:
        # Verify till belongs to user's organization
        till = db.query(Till).filter(
            Till.id == till_id,
            Till.organization_id == current_user.organization_id,
        ).first()
        if not till:
            raise HTTPException(status_code=403, detail="Access denied to this till")
        query = query.filter(Sale.till_id == till_id)
    
    if status:
        query = query.filter(Sale.status == status)

    # Count total
    total = query.count()

    # Apply pagination
    sales = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()

    return SaleListResponse(
        items=[SaleResponse.from_orm(sale) for sale in sales],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/sales/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get sale details including line items.

    - **sale_id**: Sale ID
    - Returns: 200 with Sale details including line items
    - Error: 404 if not found or 403 if not authorized
    """
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found")
    
    # Check authorization
    if sale.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this sale")

    return SaleResponse.from_orm(sale)



@router.post("/sales/{sale_id}/commit", response_model=SaleCommitResponse)
def commit_sale(
    sale_id: int,
    commit_data: SaleCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Commit a pending sale (idempotent).

    - **sale_id**: Sale ID to commit
    - **user_id**: User performing the commit
    - Returns: 200 with committed Sale
    - IDEMPOTENT: Calling twice returns 200, doesn't double-process
    - Error: 404 if sale not found, 409 if already committed

    On commit:
    - Sale status changes from PENDING to COMPLETED
    - InventoryMovements are generated (idempotent - only if not already created)
    """
    # Get sale
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found")
    
    # Check authorization
    if sale.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Access denied to this sale")

    # Check if already committed (idempotency)
    if sale.status == "COMPLETED":
        # Return 200 with the sale (idempotent - no error)
        return SaleCommitResponse.from_orm(sale)

    try:
        # Commit the sale
        SaleService.commit_pending_sale(
            sale_id=sale_id,
            recorded_by_id=commit_data.user_id,
            db=db,
        )

        # Refresh sale to get updated status
        db.refresh(sale)
        return SaleCommitResponse.from_orm(sale)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


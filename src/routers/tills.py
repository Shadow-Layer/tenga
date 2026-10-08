"""Till management and session lifecycle endpoints.

This module provides endpoints for managing point-of-sale tills.
Operations include:
- Create and list tills
- Open till sessions (login/start of day)
- Close till sessions (logout/end of day)
- Query till status and session information

Till Sessions:
- Each till can have multiple sessions over time
- Sessions track opening and closing balances
- Sessions are associated with an operator/cashier
- Session state tracks: NO_SESSION, OPEN, CLOSED

Till Management:
- Tills are location-specific
- Each till maintains its own session history
- Sessions record opening and closing balances for reconciliation
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import Till, Location, TillSession, Organization
from src.services.till_service import TillService
from src.schemas.till import (
    TillCreate,
    TillResponse,
    TillStatusResponse,
    TillSessionOpen,
    TillSessionClose,
    TillSessionOpenResponse,
    TillSessionCloseResponse,
    PaginatedTillResponse,
)

router = APIRouter()


@router.post("/", status_code=201, response_model=TillResponse)
def create_till(
    till_create: TillCreate,
    db: Session = Depends(get_db),
) -> TillResponse:
    """Create a new till.

    Args:
        till_create: Till creation request
        db: Database session

    Returns:
        Created till

    Raises:
        404: If location not found
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == till_create.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Create till
    till = Till(
        organization_id=location.organization_id,
        location_id=till_create.location_id,
        code=till_create.code,
        name=till_create.name,
        is_active=True,
    )

    db.add(till)
    db.commit()
    db.refresh(till)

    return TillResponse.from_orm(till)


@router.get("/", response_model=PaginatedTillResponse)
def list_tills(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    location_id: int = Query(None, description="Optional filter by location ID"),
    db: Session = Depends(get_db),
) -> PaginatedTillResponse:
    """List all tills with optional filtering.

    Args:
        skip: Number of records to skip
        limit: Number of records to return
        location_id: Optional filter by location
        db: Database session

    Returns:
        Paginated list of tills
    """
    query = db.query(Till)

    if location_id is not None:
        query = query.filter(Till.location_id == location_id)

    total = query.count()
    tills = query.offset(skip).limit(limit).all()

    return PaginatedTillResponse(
        items=[TillResponse.from_orm(till) for till in tills],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{till_id}", response_model=TillResponse)
def get_till(
    till_id: int,
    db: Session = Depends(get_db),
) -> TillResponse:
    """Get till details.

    Args:
        till_id: Till ID
        db: Database session

    Returns:
        Till details

    Raises:
        404: If till not found
    """
    till = db.query(Till).filter(Till.id == till_id).first()
    if not till:
        raise HTTPException(status_code=404, detail="Till not found")

    return TillResponse.from_orm(till)


@router.get("/{till_id}/status", response_model=TillStatusResponse)
def get_till_status(
    till_id: int,
    db: Session = Depends(get_db),
) -> TillStatusResponse:
    """Get current till session status.

    Args:
        till_id: Till ID
        db: Database session

    Returns:
        Current session status

    Raises:
        404: If till not found
    """
    till = db.query(Till).filter(Till.id == till_id).first()
    if not till:
        raise HTTPException(status_code=404, detail="Till not found")

    # Get current open session if any
    current_session = TillService.get_current_open_session(till_id, db)

    if current_session:
        return TillStatusResponse(
            till_id=till_id,
            session_id=current_session.id,
            is_open=True,
            opened_at=current_session.opened_at,
            closed_at=None,
            session_state="OPEN",
            operator_id=current_session.operator_id,
            opening_balance=float(current_session.opening_balance),
        )
    else:
        return TillStatusResponse(
            till_id=till_id,
            session_id=None,
            is_open=False,
            opened_at=None,
            closed_at=None,
            session_state="NO_SESSION",
            operator_id=None,
            opening_balance=None,
        )


@router.post("/{till_id}/open", status_code=201, response_model=TillSessionOpenResponse)
def open_till_session(
    till_id: int,
    session_open: TillSessionOpen,
    db: Session = Depends(get_db),
) -> TillSessionOpenResponse:
    """Open a new till session.

    Args:
        till_id: Till ID
        session_open: Session open request
        db: Database session

    Returns:
        Opened session details

    Raises:
        404: If till not found
        409: If till already has open session
        400: If subscription is LIMITED
    """
    # Get till and verify it exists
    till = db.query(Till).filter(Till.id == till_id).first()
    if not till:
        raise HTTPException(status_code=404, detail="Till not found")

    # Check if subscription allows opening (not LIMITED)
    try:
        TillService.assert_open_allowed(till.organization_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if till already has open session
    existing_open = db.query(TillSession).filter(
        TillSession.till_id == till_id,
        TillSession.status == "OPEN",
    ).first()
    if existing_open:
        raise HTTPException(
            status_code=409,
            detail="Till already has an open session",
        )

    # Create new session
    try:
        till_session = TillService.open_session(
            organization_id=till.organization_id,
            till_id=till_id,
            operator_id=session_open.user_id,
            opening_balance=session_open.opening_balance or 0.0,
            db=db,
        )
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))

    return TillSessionOpenResponse(
        till_id=till_session.till_id,
        session_id=till_session.id,
        session_number=till_session.session_number,
        opened_at=till_session.opened_at,
        operator_id=till_session.operator_id,
        opening_balance=float(till_session.opening_balance),
        is_open=True,
    )


@router.post("/{till_id}/close", status_code=200, response_model=TillSessionCloseResponse)
def close_till_session(
    till_id: int,
    session_close: TillSessionClose,
    db: Session = Depends(get_db),
) -> TillSessionCloseResponse:
    """Close the current till session.

    Args:
        till_id: Till ID
        session_close: Session close request
        db: Database session

    Returns:
        Closed session details

    Raises:
        404: If till or session not found
        409: If till doesn't have an open session
    """
    # Get till and verify it exists
    till = db.query(Till).filter(Till.id == till_id).first()
    if not till:
        raise HTTPException(status_code=404, detail="Till not found")

    # Get current open session
    current_session = TillService.get_current_open_session(till_id, db)
    if not current_session:
        raise HTTPException(
            status_code=409,
            detail="No open session to close",
        )

    # Close session
    try:
        till_session = TillService.close_session(
            till_session_id=current_session.id,
            closing_balance=session_close.closing_amount_cents / 100.0,
            notes=session_close.notes,
            db=db,
        )
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))

    return TillSessionCloseResponse(
        till_id=till_session.till_id,
        session_id=till_session.id,
        session_number=till_session.session_number,
        closed_at=till_session.closed_at,
        closing_balance=float(till_session.closing_balance),
        status="CLOSED",
        notes=till_session.notes,
    )

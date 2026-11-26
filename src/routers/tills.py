"""Organization-scoped till administration and session lifecycle endpoints."""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import (
    Employee,
    EmployeeTillAssignment,
    Location,
    Till,
    TillSession,
    User,
)
from src.schemas.till import (
    PaginatedTillResponse,
    PaginatedTillSessionHistory,
    TillAssignmentsResponse,
    TillAssignmentsUpdate,
    TillCashMovementCreate,
    TillCashMovementResponse,
    TillCreate,
    TillResponse,
    TillSessionClose,
    TillSessionCloseResponse,
    TillSessionOpen,
    TillSessionOpenResponse,
    TillStatusResponse,
    TillUpdate,
)
from src.security.authorization import get_current_user
from src.services.till_service import TillService

router = APIRouter()


def _admin_or_manager(user: User) -> None:
    if (user.role or "").lower() not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin or manager can administer tills",
        )


def _get_till(till_id: int, organization_id: int, db: Session) -> Till:
    till = db.query(Till).filter(
        Till.id == till_id,
        Till.organization_id == organization_id,
    ).first()
    if till is None:
        raise HTTPException(status_code=404, detail="Till not found")
    return till


def _require_assignment(till: Till, user: User, db: Session) -> None:
    try:
        TillService.require_assigned_user(till, user, db)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/", status_code=201, response_model=TillResponse)
def create_till(
    till_create: TillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillResponse:
    _admin_or_manager(current_user)
    try:
        till = TillService.create_till(
            organization_id=current_user.organization_id,
            location_id=till_create.location_id,
            code=till_create.code,
            name=till_create.name,
            db=db,
        )
    except ValueError as exc:
        detail = str(exc)
        code = (
            404 if "Location not found" in detail
            else 422 if "blank" in detail.lower()
            else 409
        )
        raise HTTPException(status_code=code, detail=detail) from exc
    return TillResponse.from_orm(till)


@router.get("/", response_model=PaginatedTillResponse)
def list_tills(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    location_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTillResponse:
    query = db.query(Till).filter(Till.organization_id == current_user.organization_id)
    if location_id is not None:
        location = db.query(Location.id).filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        ).first()
        if location is None:
            raise HTTPException(status_code=404, detail="Location not found")
        query = query.filter(Till.location_id == location_id)
    total = query.count()
    tills = query.order_by(Till.id).offset(skip).limit(limit).all()
    return PaginatedTillResponse(
        items=[TillResponse.from_orm(till) for till in tills],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/assigned", response_model=PaginatedTillResponse)
def list_assigned_tills(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTillResponse:
    employee_id = db.query(Employee.id).filter(
        Employee.organization_id == current_user.organization_id,
        Employee.user_id == current_user.id,
        Employee.is_active.is_(True),
        Employee.archived_at.is_(None),
    ).scalar()
    if employee_id is None:
        return PaginatedTillResponse(items=[], total=0, skip=skip, limit=limit)

    query = (
        db.query(Till)
        .join(EmployeeTillAssignment, EmployeeTillAssignment.till_id == Till.id)
        .filter(
            Till.organization_id == current_user.organization_id,
            Till.is_active.is_(True),
            EmployeeTillAssignment.employee_id == employee_id,
            EmployeeTillAssignment.ended_at.is_(None),
        )
    )
    total = query.count()
    tills = query.order_by(Till.id).offset(skip).limit(limit).all()
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
    current_user: User = Depends(get_current_user),
) -> TillResponse:
    return TillResponse.from_orm(
        _get_till(till_id, current_user.organization_id, db)
    )


@router.patch("/{till_id}", response_model=TillResponse)
def update_till(
    till_id: int,
    till_update: TillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillResponse:
    _admin_or_manager(current_user)
    till = _get_till(till_id, current_user.organization_id, db)
    changes = till_update.dict(exclude_unset=True)
    if not changes:
        return TillResponse.from_orm(till)
    try:
        till = TillService.update_till(till, changes, db)
    except ValueError as exc:
        detail = str(exc)
        code = (
            404 if "Location not found" in detail
            else 422 if "blank" in detail.lower()
            else 409
        )
        raise HTTPException(status_code=code, detail=detail) from exc
    return TillResponse.from_orm(till)


@router.post("/{till_id}/deactivate", response_model=TillResponse)
def deactivate_till(
    till_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillResponse:
    _admin_or_manager(current_user)
    till = _get_till(till_id, current_user.organization_id, db)
    try:
        till = TillService.deactivate_till(till, db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TillResponse.from_orm(till)


@router.get("/{till_id}/assignments", response_model=TillAssignmentsResponse)
def get_till_assignments(
    till_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillAssignmentsResponse:
    _admin_or_manager(current_user)
    till = _get_till(till_id, current_user.organization_id, db)
    employee_ids = [
        row[0] for row in db.query(EmployeeTillAssignment.employee_id)
        .filter(
            EmployeeTillAssignment.till_id == till.id,
            EmployeeTillAssignment.ended_at.is_(None),
        )
        .order_by(EmployeeTillAssignment.employee_id)
        .all()
    ]
    return TillAssignmentsResponse(till_id=till.id, employee_ids=employee_ids)


@router.put("/{till_id}/assignments", response_model=TillAssignmentsResponse)
def set_till_assignments(
    till_id: int,
    request: TillAssignmentsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillAssignmentsResponse:
    _admin_or_manager(current_user)
    till = _get_till(till_id, current_user.organization_id, db)
    try:
        employees = TillService.set_assignments(till, request.employee_ids, db)
    except ValueError as exc:
        detail = str(exc)
        code = 409 if "session is open" in detail.lower() else 422
        raise HTTPException(status_code=code, detail=detail) from exc
    return TillAssignmentsResponse(
        till_id=till.id,
        employee_ids=sorted(employee.id for employee in employees),
    )


@router.post(
        "/{till_id}/cash-movements",
        status_code=201,
        response_model=TillCashMovementResponse,
)
def create_till_cash_movement(
        till_id: int,
        request: TillCashMovementCreate,
        response: Response,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> TillCashMovementResponse:
        till = _get_till(till_id, current_user.organization_id, db)
        if not till.is_active:
            raise HTTPException(status_code=409, detail="Till is inactive")
        try:
            movement, replayed = TillService.create_cash_movement(
                till_id=till.id,
                organization_id=current_user.organization_id,
                actor=current_user,
                operation_id=request.operation_id,
                movement_type=request.movement_type,
                amount=request.amount,
                reason=request.reason,
                reference=request.reference,
                db=db,
            )
        except ValueError as exc:
            detail = str(exc)
            if (
                "assigned" in detail.lower()
                or "operator" in detail.lower()
                or "employee" in detail.lower()
                or "active organization user" in detail.lower()
            ):
                code = 403
            elif (
                "different payload" in detail.lower()
                or "already used" in detail.lower()
                or "conflicts with existing" in detail.lower()
            ):
                code = 409
            elif (
                "open till session" in detail.lower()
                or "session is open" in detail.lower()
                or "session" in detail.lower()
            ):
                code = 409
            else:
                code = 422
            raise HTTPException(status_code=code, detail=detail) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if replayed:
            response.status_code = 200
        return TillCashMovementResponse(**movement)


@router.get("/{till_id}/status", response_model=TillStatusResponse)
def get_till_status(
    till_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillStatusResponse:
    _get_till(till_id, current_user.organization_id, db)
    current_session = TillService.get_current_open_session(
        till_id, db, organization_id=current_user.organization_id
    )
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
            currency_code=current_session.currency_code,
        )
    return TillStatusResponse(
        till_id=till_id,
        session_id=None,
        is_open=False,
        opened_at=None,
        closed_at=None,
        session_state="NO_SESSION",
        operator_id=None,
        opening_balance=None,
        currency_code=None,
    )


@router.get("/{till_id}/sessions", response_model=PaginatedTillSessionHistory)
def list_till_sessions(
    till_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTillSessionHistory:
    _get_till(till_id, current_user.organization_id, db)
    base_query = db.query(TillSession).filter(
        TillSession.till_id == till_id,
        TillSession.organization_id == current_user.organization_id,
    )
    total = base_query.count()
    sessions = base_query.order_by(
        TillSession.created_at.desc(), TillSession.id.desc()
    ).offset(skip).limit(limit).all()
    return PaginatedTillSessionHistory(
        items=sessions, total=total, skip=skip, limit=limit
    )


@router.post("/{till_id}/open", status_code=201, response_model=TillSessionOpenResponse)
def open_till_session(
    till_id: int,
    session_open: TillSessionOpen,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillSessionOpenResponse:
    if session_open.user_id is not None and session_open.user_id != current_user.id:
        raise HTTPException(
            status_code=422,
            detail="Operator identity is derived from the authenticated user",
        )
    till = _get_till(till_id, current_user.organization_id, db)
    if not till.is_active:
        raise HTTPException(status_code=409, detail="Till is inactive")
    _require_assignment(till, current_user, db)
    try:
        TillService.assert_open_allowed(till.organization_id, db)
        till_session = TillService.open_session(
            organization_id=till.organization_id,
            till_id=till_id,
            operator_id=current_user.id,
            opening_balance=session_open.opening_balance or Decimal("0.00"),
            db=db,
            enforce_assignment=True,
        )
    except ValueError as exc:
        detail = str(exc)
        code = 400 if "LIMITED mode" in detail else 409
        raise HTTPException(status_code=code, detail=detail) from exc
    return TillSessionOpenResponse(
        till_id=till_session.till_id,
        session_id=till_session.id,
        session_number=till_session.session_number,
        opened_at=till_session.opened_at,
        operator_id=till_session.operator_id,
        opening_balance=float(till_session.opening_balance),
        currency_code=till_session.currency_code,
        is_open=True,
    )


@router.post("/{till_id}/close", response_model=TillSessionCloseResponse)
def close_till_session(
    till_id: int,
    session_close: TillSessionClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TillSessionCloseResponse:
    if session_close.user_id is not None and session_close.user_id != current_user.id:
        raise HTTPException(
            status_code=422,
            detail="Closing identity is derived from the authenticated user",
        )
    till = _get_till(till_id, current_user.organization_id, db)
    current_session = TillService.get_current_open_session(
        till_id, db, organization_id=current_user.organization_id
    )
    if current_session is None:
        raise HTTPException(status_code=409, detail="No open session to close")
    if current_session.id != session_close.session_id:
        raise HTTPException(
            status_code=409,
            detail="Till session changed. Refresh the session status before closing.",
        )
    if (
        current_session.operator_id != current_user.id
        and (current_user.role or "").lower() not in ("admin", "manager")
    ):
        raise HTTPException(
            status_code=403,
            detail="Only the session operator or an admin/manager can close this till",
        )
    try:
        till_session = TillService.close_session(
            till_session_id=current_session.id,
            closing_balance=session_close.closing_balance,
            notes=session_close.notes,
            db=db,
            closed_by_id=current_user.id,
            actor=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TillSessionCloseResponse(
        till_id=till_session.till_id,
        session_id=till_session.id,
        session_number=till_session.session_number,
        closed_at=till_session.closed_at,
        closing_balance=float(till_session.closing_balance),
        expected_closing_balance=float(till_session.expected_closing_balance),
        cash_variance=float(till_session.cash_variance),
        currency_code=till_session.currency_code,
        status="CLOSED",
        notes=till_session.notes,
    )

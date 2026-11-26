"""Tenant-scoped employee administration API."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import (
    Employee,
    EmployeeLocationAssignment,
    EmployeeTillAssignment,
    Location,
    Organization,
    Till,
    User,
)
from src.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from src.security.authorization import get_current_user


router = APIRouter()
_optional_bearer = HTTPBearer(auto_error=False)


async def _authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await get_current_user(credentials, db)


def _require_tenant(org_id: int, user: User, db: Session) -> None:
    if user.organization_id != org_id or not db.query(Organization.id).filter(
        Organization.id == org_id
    ).first():
        raise HTTPException(status_code=404, detail="Organization not found")


def _require_manager_or_admin(user: User) -> None:
    if user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Only an admin or manager can manage employees",
        )


def _get_employee(org_id: int, employee_id: int, db: Session) -> Employee:
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.organization_id == org_id,
    ).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


def _validate_user_link(
    org_id: int,
    user_id: Optional[int],
    db: Session,
    employee_id: Optional[int] = None,
) -> None:
    if user_id is None:
        return
    if not db.query(User.id).filter(
        User.id == user_id,
        User.organization_id == org_id,
    ).first():
        raise HTTPException(status_code=404, detail="User not found")
    linked = db.query(Employee.id).filter(Employee.user_id == user_id)
    if employee_id is not None:
        linked = linked.filter(Employee.id != employee_id)
    if linked.first() is not None:
        raise HTTPException(status_code=409, detail="User is already linked to an employee")


def _validate_assignments(
    org_id: int,
    location_ids: Optional[list[int]],
    till_ids: Optional[list[int]],
    db: Session,
) -> tuple[Optional[list[int]], Optional[list[int]]]:
    locations = None if location_ids is None else list(dict.fromkeys(location_ids))
    tills = None if till_ids is None else list(dict.fromkeys(till_ids))
    if locations:
        found = db.query(Location.id).filter(
            Location.id.in_(locations),
            Location.organization_id == org_id,
            Location.is_active.is_(True),
        ).all()
        if len(found) != len(locations):
            raise HTTPException(status_code=404, detail="One or more locations not found")
    if tills:
        found = db.query(Till.id).filter(
            Till.id.in_(tills),
            Till.organization_id == org_id,
            Till.is_active.is_(True),
        ).all()
        if len(found) != len(tills):
            raise HTTPException(status_code=404, detail="One or more tills not found")
    return locations, tills


def _replace_assignments(
    employee: Employee,
    location_ids: Optional[list[int]],
    till_ids: Optional[list[int]],
    db: Session,
) -> None:
    if location_ids is not None:
        active_locations = db.query(EmployeeLocationAssignment).filter(
            EmployeeLocationAssignment.employee_id == employee.id,
            EmployeeLocationAssignment.ended_at.is_(None),
        ).all()
        active_location_ids = {row.location_id for row in active_locations}
        desired_location_ids = set(location_ids)
        now = datetime.utcnow()
        for assignment in active_locations:
            if assignment.location_id not in desired_location_ids:
                assignment.ended_at = now
        db.add_all(
            EmployeeLocationAssignment(employee_id=employee.id, location_id=value)
            for value in desired_location_ids - active_location_ids
        )

    if till_ids is not None:
        active_tills = db.query(EmployeeTillAssignment).filter(
            EmployeeTillAssignment.employee_id == employee.id,
            EmployeeTillAssignment.ended_at.is_(None),
        ).all()
        active_till_ids = {row.till_id for row in active_tills}
        desired_till_ids = set(till_ids)
        now = datetime.utcnow()
        for assignment in active_tills:
            if assignment.till_id not in desired_till_ids:
                assignment.ended_at = now
        db.add_all(
            EmployeeTillAssignment(employee_id=employee.id, till_id=value)
            for value in desired_till_ids - active_till_ids
        )


def _response(employee: Employee, db: Session) -> EmployeeResponse:
    return EmployeeResponse(
        id=employee.id,
        organization_id=employee.organization_id,
        employee_number=employee.employee_number,
        full_name=employee.full_name,
        email=employee.email,
        phone=employee.phone,
        title=employee.title,
        user_id=employee.user_id,
        is_active=employee.is_active,
        archived_at=employee.archived_at,
        location_ids=[
            row[0] for row in db.query(EmployeeLocationAssignment.location_id)
            .filter(
                EmployeeLocationAssignment.employee_id == employee.id,
                EmployeeLocationAssignment.ended_at.is_(None),
            )
            .order_by(EmployeeLocationAssignment.location_id).all()
        ],
        till_ids=[
            row[0] for row in db.query(EmployeeTillAssignment.till_id)
            .filter(
                EmployeeTillAssignment.employee_id == employee.id,
                EmployeeTillAssignment.ended_at.is_(None),
            )
            .order_by(EmployeeTillAssignment.till_id).all()
        ],
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Employee number, user link, or assignment already exists",
        ) from exc


@router.post(
    "/{org_id}/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    org_id: int,
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeResponse:
    _require_tenant(org_id, user, db)
    _require_manager_or_admin(user)
    if db.query(Employee.id).filter(
        Employee.organization_id == org_id,
        Employee.employee_number == data.employee_number,
    ).first():
        raise HTTPException(status_code=409, detail="Employee number already exists")
    _validate_user_link(org_id, data.user_id, db)
    location_ids = till_ids = None
    if "location_ids" in data.model_fields_set or "till_ids" in data.model_fields_set:
        location_ids, till_ids = _validate_assignments(
            org_id,
            data.location_ids if "location_ids" in data.model_fields_set else None,
            data.till_ids if "till_ids" in data.model_fields_set else None,
            db,
        )
    employee = Employee(
        organization_id=org_id,
        employee_number=data.employee_number,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        title=data.title,
        user_id=data.user_id,
        is_active=True,
    )
    db.add(employee)
    try:
        db.flush()
        _replace_assignments(employee, location_ids, till_ids, db)
        _commit_or_conflict(db)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Employee number, user link, or assignment already exists",
        ) from exc
    db.refresh(employee)
    return _response(employee, db)


@router.get("/{org_id}/employees", response_model=EmployeeListResponse)
def list_employees(
    org_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_archived: bool = False,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeListResponse:
    _require_tenant(org_id, user, db)
    query = db.query(Employee).filter(Employee.organization_id == org_id)
    if not include_archived:
        query = query.filter(Employee.archived_at.is_(None))
    if active is not None:
        query = query.filter(Employee.is_active.is_(active))
    total = query.count()
    items = query.order_by(Employee.id).offset(skip).limit(limit).all()
    return EmployeeListResponse(
        items=[_response(item, db) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{org_id}/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    org_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeResponse:
    _require_tenant(org_id, user, db)
    return _response(_get_employee(org_id, employee_id, db), db)


@router.patch("/{org_id}/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    org_id: int,
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeResponse:
    _require_tenant(org_id, user, db)
    _require_manager_or_admin(user)
    employee = _get_employee(org_id, employee_id, db)
    if employee.archived_at is not None:
        raise HTTPException(status_code=409, detail="Archived employees cannot be updated")

    values = data.model_dump(exclude_unset=True, exclude={"location_ids", "till_ids"})
    if "employee_number" in values and values["employee_number"] != employee.employee_number:
        duplicate = db.query(Employee.id).filter(
            Employee.organization_id == org_id,
            Employee.employee_number == values["employee_number"],
            Employee.id != employee.id,
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Employee number already exists")
    if "user_id" in values:
        _validate_user_link(org_id, values["user_id"], db, employee.id)
    location_ids, till_ids = _validate_assignments(
        org_id, data.location_ids, data.till_ids, db
    )
    for field, value in values.items():
        setattr(employee, field, value)
    _replace_assignments(employee, location_ids, till_ids, db)
    _commit_or_conflict(db)
    db.refresh(employee)
    return _response(employee, db)


@router.post(
    "/{org_id}/employees/{employee_id}/deactivate",
    response_model=EmployeeResponse,
)
def deactivate_employee(
    org_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeResponse:
    _require_tenant(org_id, user, db)
    _require_manager_or_admin(user)
    employee = _get_employee(org_id, employee_id, db)
    employee.is_active = False
    if employee.user is not None:
        employee.user.is_active = False
    _replace_assignments(employee, [], [], db)
    _commit_or_conflict(db)
    db.refresh(employee)
    return _response(employee, db)


@router.post(
    "/{org_id}/employees/{employee_id}/archive",
    response_model=EmployeeResponse,
)
def archive_employee(
    org_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_authenticated_user),
) -> EmployeeResponse:
    _require_tenant(org_id, user, db)
    _require_manager_or_admin(user)
    employee = _get_employee(org_id, employee_id, db)
    employee.is_active = False
    if employee.user is not None:
        employee.user.is_active = False
    _replace_assignments(employee, [], [], db)
    if employee.archived_at is None:
        employee.archived_at = datetime.utcnow()
    _commit_or_conflict(db)
    db.refresh(employee)
    return _response(employee, db)

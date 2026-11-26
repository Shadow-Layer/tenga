"""Organizations router - REST API for organization management.

This module provides endpoints for managing organizations (multi-tenancy).
Operations include:
- Create and list organizations
- Retrieve organization details
- Manage organization settings
- Activate/deactivate organizations

Organizations are the top-level container for all POS data including:
- Products and inventory
- Locations (stores/warehouses)
- Users and staff
- Till sessions and sales
- Subscription information
"""
import hmac
from typing import Optional

import src.config as app_config
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.database.config import Base, get_db
from src.models.entities import InventoryMovement, Organization, Sale, User
from src.schemas.bootstrap import (
    InstallationBootstrapRequest,
    InstallationBootstrapResponse,
)
from src.schemas.organization import (
    OrganizationResponse,
    OrganizationListResponse,
    OrganizationUpdate,
)
from src.security.authorization import get_current_user
from src.security.password import hash_password

router = APIRouter()


@router.post(
    "",
    status_code=410,
    summary="Direct organization creation is disabled",
    description="Use the operator-authorized first-install bootstrap endpoint.",
)
def create_organization():
    """Reject anonymous organization creation; use the protected bootstrap."""
    raise HTTPException(
        status_code=410,
        detail="Direct organization creation is disabled. Use first-install bootstrap.",
    )


def _lock_bootstrap_state(db: Session) -> None:
    """Serialize initialization across workers using the database transaction."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    elif dialect == "postgresql":
        db.execute(text("LOCK TABLE organization IN EXCLUSIVE MODE"))
    else:
        raise HTTPException(
            status_code=503,
            detail="First-install bootstrap is not supported by this database.",
        )


def _is_fresh_installation(db: Session) -> bool:
    """Reject any application data, not only organization and user rows."""
    return all(
        db.execute(select(1).select_from(table).limit(1)).first() is None
        for table in Base.metadata.sorted_tables
    )


@router.post(
    "/bootstrap",
    response_model=InstallationBootstrapResponse,
    status_code=201,
    summary="Initialize a fresh installation",
    description="Create the local organization and its first administrator once.",
)
def bootstrap_installation(
    setup_data: InstallationBootstrapRequest,
    db: Session = Depends(get_db),
    setup_secret: Optional[str] = Header(default=None, alias="X-Setup-Secret"),
):
    """Create one organization and owner on an empty database only."""
    configured_secret = app_config.INITIAL_SETUP_SECRET
    if len(configured_secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="First-install bootstrap is not configured with a sufficiently strong secret.",
        )
    if setup_secret is None or not hmac.compare_digest(
        setup_secret.encode("utf-8"),
        configured_secret.encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Invalid setup secret.")

    try:
        _lock_bootstrap_state(db)
        if not _is_fresh_installation(db):
            raise HTTPException(
                status_code=409,
                detail="Bootstrap is only available on a fresh installation.",
            )

        organization = Organization(
            name=setup_data.organization.name,
            code=setup_data.organization.code,
            description=setup_data.organization.description,
            phone=setup_data.organization.phone,
            email=setup_data.organization.email,
            address=setup_data.organization.address,
            region=setup_data.organization.region,
            timezone=setup_data.organization.timezone,
            currency_code=setup_data.organization.currency_code,
            is_active=True,
        )
        db.add(organization)
        db.flush()

        owner = User(
            organization_id=organization.id,
            email=setup_data.owner.email,
            username=setup_data.owner.username,
            full_name=setup_data.owner.full_name,
            password_hash=hash_password(setup_data.owner.password),
            role="admin",
            is_active=True,
        )
        db.add(owner)
        db.commit()
        db.refresh(organization)
        db.refresh(owner)
        return {"organization": organization, "owner": owner}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The installation could not be initialized with these organization or owner details.",
        ) from error
    except Exception:
        db.rollback()
        raise


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization",
    description="Get organization details by ID",
)
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get organization details by ID.
    
    Args:
        org_id: Organization ID
        db: Database session
        
    Returns:
        OrganizationResponse: Organization details
        
    Raises:
        404: If organization not found
    """
    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.id == current_user.organization_id,
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update organization settings",
    description="Update organization details and operational settings.",
)
def update_organization(
    org_id: int,
    update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update this tenant's organization without rewriting financial history."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can update organization settings.")

    organization = (
        db.query(Organization)
        .filter(
            Organization.id == org_id,
            Organization.id == current_user.organization_id,
        )
        .with_for_update()
        .first()
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    fields = update.model_dump(exclude_unset=True, exclude={"confirm_legacy_currency"})
    if not fields:
        raise HTTPException(status_code=422, detail="At least one organization setting is required.")

    if "currency_code" in fields:
        requested_currency = fields["currency_code"]
        if requested_currency is None:
            raise HTTPException(status_code=422, detail="Currency code cannot be empty.")
        if requested_currency != organization.currency_code:
            has_activity = (
                db.query(InventoryMovement.id)
                .filter(InventoryMovement.organization_id == organization.id)
                .first()
                is not None
                or db.query(Sale.id)
                .filter(Sale.organization_id == organization.id)
                .first()
                is not None
            )
            if has_activity and not (
                organization.currency_code is None and update.confirm_legacy_currency
            ):
                detail = "Currency cannot be changed after inventory or sales activity."
                if organization.currency_code is None:
                    detail = (
                        "Currency cannot be changed after activity unless you explicitly confirm "
                        "a default for future operations; historical records remain unchanged."
                    )
                raise HTTPException(status_code=409, detail=detail)

    for field, value in fields.items():
        setattr(organization, field, value)
    try:
        db.commit()
        db.refresh(organization)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Organization settings conflict with an existing record.",
        ) from error
    return organization


@router.get(
    "",
    response_model=OrganizationListResponse,
    summary="List organizations",
    description="Get paginated list of all organizations",
)
def list_organizations(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all organizations with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        OrganizationListResponse: Paginated list of organizations
    """
    query = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    )
    total = query.count()
    organizations = query.offset(max(skip, 0)).limit(min(max(limit, 1), 100)).all()
    
    return OrganizationListResponse(
        items=organizations,
        total=total,
        skip=skip,
        limit=limit,
    )

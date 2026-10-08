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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.config import get_db
from src.models.entities import Organization
from src.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationListResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=201,
    summary="Create organization",
    description="Create a new organization",
)
def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
):
    """Create a new organization.
    
    Args:
        org_data: Organization creation data (name, description, code)
        db: Database session
        
    Returns:
        OrganizationResponse: Created organization
        
    Raises:
        409: If organization name or code already exists
    """
    # Check if organization with same name or code already exists
    existing = db.query(Organization).filter(
        (Organization.name == org_data.name) | (Organization.code == org_data.code)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organization with name '{org_data.name}' or code '{org_data.code}' already exists"
        )
    
    # Create new organization
    org = Organization(
        name=org_data.name,
        code=org_data.code,
        description=org_data.description,
        is_active=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return org


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization",
    description="Get organization details by ID",
)
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
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
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


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
):
    """List all organizations with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        OrganizationListResponse: Paginated list of organizations
    """
    total = db.query(Organization).count()
    organizations = db.query(Organization).offset(skip).limit(limit).all()
    
    return OrganizationListResponse(
        items=organizations,
        total=total,
        skip=skip,
        limit=limit,
    )

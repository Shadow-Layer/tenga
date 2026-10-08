"""Locations API router.

This module provides endpoints for managing store locations/warehouses.
Operations include:
- Create and list store locations
- Retrieve location details
- Update location information
- Delete locations

Each location can store inventory and have tills assigned to it.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.config import get_db
from src.models.entities import Location, Organization
from src.schemas.location import LocationCreate, LocationResponse, LocationListResponse

router = APIRouter()


@router.post("/locations", response_model=LocationResponse, status_code=201, tags=["locations"])
def create_location(location_data: LocationCreate, db: Session = Depends(get_db)):
    """Create a new location.
    
    Args:
        location_data: Location creation data
        db: Database session
        
    Returns:
        Created location
        
    Raises:
        404: Organization not found
    """
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == location_data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Create location
    location = Location(
        name=location_data.name,
        code=location_data.code,
        description=location_data.description,
        organization_id=location_data.organization_id,
    )
    
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("/locations", response_model=LocationListResponse, tags=["locations"])
def list_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    organization_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """List locations with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return
        organization_id: Optional filter by organization
        db: Database session
        
    Returns:
        Paginated list of locations
    """
    query = db.query(Location)
    
    if organization_id is not None:
        query = query.filter(Location.organization_id == organization_id)
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return LocationListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/locations/{location_id}", response_model=LocationResponse, tags=["locations"])
def get_location(location_id: int, db: Session = Depends(get_db)):
    """Get location details.
    
    Args:
        location_id: Location ID
        db: Database session
        
    Returns:
        Location details
        
    Raises:
        404: Location not found
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return location

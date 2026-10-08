"""Location Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LocationCreate(BaseModel):
    """Schema for creating a location."""
    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    code: str = Field(..., min_length=1, max_length=50, description="Location code/identifier")
    description: Optional[str] = Field(None, max_length=1000, description="Location description")
    organization_id: int = Field(..., description="Organization ID")


class LocationResponse(BaseModel):
    """Schema for location response."""
    id: int = Field(..., description="Location ID")
    name: str = Field(..., description="Location name")
    code: str = Field(..., description="Location code")
    description: Optional[str] = Field(None, description="Location description")
    organization_id: int = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class LocationListResponse(BaseModel):
    """Schema for paginated location list response."""
    items: List[LocationResponse] = Field(..., description="List of locations")
    total: int = Field(..., description="Total number of locations")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")

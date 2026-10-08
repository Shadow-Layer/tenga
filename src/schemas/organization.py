"""Pydantic schemas for organization management."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    """Request schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, max_length=1000, description="Organization description")
    code: str = Field(..., min_length=1, max_length=50, description="Organization code")


class OrganizationResponse(BaseModel):
    """Response schema for a single organization."""
    id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    code: str = Field(..., description="Organization code")
    description: Optional[str] = Field(None, description="Organization description")
    is_active: bool = Field(..., description="Whether organization is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """Response schema for paginated organization list."""
    items: List[OrganizationResponse] = Field(..., description="List of organizations")
    total: int = Field(..., description="Total number of organizations")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")

"""Pydantic schemas for organization management."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class OrganizationCreate(BaseModel):
    """Request schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, max_length=1000, description="Organization description")
    code: str = Field(..., min_length=1, max_length=50, description="Organization code")
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=2000)
    region: Optional[str] = Field(None, max_length=100)
    timezone: str = Field("UTC", min_length=1, max_length=100)
    currency_code: str = Field(
        "USD",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class OrganizationUpdate(BaseModel):
    """Organization settings that an administrator may update."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=2000)
    region: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, min_length=1, max_length=100)
    currency_code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    confirm_legacy_currency: bool = False

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class OrganizationResponse(BaseModel):
    """Response schema for a single organization."""
    id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    code: str = Field(..., description="Organization code")
    description: Optional[str] = Field(None, description="Organization description")
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    timezone: str = "UTC"
    currency_code: Optional[str] = None
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

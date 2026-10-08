"""Pydantic schemas for subscription endpoints."""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """Request schema for creating a subscription."""
    plan_type: Literal["MONTHLY", "ANNUAL"] = Field(
        ..., description="Billing plan type"
    )
    start_date: datetime = Field(
        ..., description="Subscription start date (ISO 8601 format)"
    )


class SubscriptionResponse(BaseModel):
    """Response schema for subscription details."""
    id: int = Field(..., description="Subscription ID")
    organization_id: int = Field(..., description="Organization ID")
    plan: str = Field(..., description="Billing plan (e.g., BASIC, PROFESSIONAL)")
    term: str = Field(..., description="Billing term (MONTHLY, ANNUAL)")
    state: str = Field(..., description="Current state (ACTIVE, GRACE, LIMITED)")
    expiry_date: datetime = Field(..., description="Subscription expiry date")
    grace_end_date: Optional[datetime] = Field(
        None, description="Grace period end date (if in grace)"
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    class Config:
        from_attributes = True


class RenewalRequest(BaseModel):
    """Request schema for subscription renewal."""
    new_expiry_date: Optional[datetime] = Field(
        None, description="New expiry date (optional - service can auto-compute)"
    )


class SubscriptionStateResponse(BaseModel):
    """Response schema for subscription state details."""
    state: Literal["ACTIVE", "GRACE", "LIMITED"] = Field(
        ..., description="Current subscription state"
    )
    expiry_date: datetime = Field(..., description="Subscription expiry date")
    grace_end_date: Optional[datetime] = Field(
        None, description="Grace period end date"
    )
    days_remaining: int = Field(
        ..., description="Days until expiry (negative if expired)"
    )
    days_in_grace: int = Field(
        ..., description="Days remaining in grace period (0 if not in grace)"
    )
    operational: bool = Field(
        ..., description="True if ACTIVE or GRACE, False if LIMITED"
    )

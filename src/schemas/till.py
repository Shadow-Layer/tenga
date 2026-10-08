"""Pydantic schemas for till management and session operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TillCreate(BaseModel):
    """Request schema for creating a new till."""
    location_id: int = Field(..., description="Location ID where till is placed")
    code: str = Field(..., description="Till code/identifier")
    name: str = Field(..., description="Till display name")

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": 1,
                "code": "TILL001",
                "name": "Till 1",
            }
        }


class TillResponse(BaseModel):
    """Response schema for till details."""
    id: int = Field(..., description="Till ID")
    organization_id: int = Field(..., description="Organization ID")
    location_id: int = Field(..., description="Location ID")
    code: str = Field(..., description="Till code")
    name: str = Field(..., description="Till name")
    is_active: bool = Field(default=True, description="Whether till is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "organization_id": 1,
                "location_id": 1,
                "code": "TILL001",
                "name": "Till 1",
                "is_active": True,
                "created_at": "2026-10-07T16:13:50.467Z",
                "updated_at": "2026-10-07T16:13:50.467Z",
            }
        }


class TillSessionOpen(BaseModel):
    """Request schema for opening a till session."""
    user_id: int = Field(..., description="Operator user ID")
    opening_balance: Optional[float] = Field(
        0.0, description="Optional opening cash balance"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "opening_balance": 5000.0,
            }
        }


class TillSessionClose(BaseModel):
    """Request schema for closing a till session."""
    user_id: int = Field(..., description="User ID closing the till")
    closing_amount_cents: float = Field(
        ..., description="Final cash amount in cents"
    )
    notes: Optional[str] = Field(None, description="Optional closing notes")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "closing_amount_cents": 50000.0,
                "notes": "Balance matches expected amount",
            }
        }


class TillStatusResponse(BaseModel):
    """Response schema for current till session status."""
    till_id: int = Field(..., description="Till ID")
    session_id: Optional[int] = Field(None, description="Current session ID")
    is_open: bool = Field(default=False, description="Whether till is currently open")
    opened_at: Optional[datetime] = Field(None, description="Session opening timestamp")
    closed_at: Optional[datetime] = Field(None, description="Session closing timestamp")
    session_state: str = Field(default="NO_SESSION", description="Session state (NO_SESSION, OPEN, CLOSED)")
    operator_id: Optional[int] = Field(None, description="Operator user ID")
    opening_balance: Optional[float] = Field(None, description="Opening cash balance")

    class Config:
        json_schema_extra = {
            "example": {
                "till_id": 1,
                "session_id": 10,
                "is_open": True,
                "opened_at": "2026-10-07T16:13:50.467Z",
                "closed_at": None,
                "session_state": "OPEN",
                "operator_id": 1,
                "opening_balance": 5000.0,
            }
        }


class TillSessionOpenResponse(BaseModel):
    """Response schema for successfully opened till session."""
    till_id: int = Field(..., description="Till ID")
    session_id: int = Field(..., description="Session ID")
    session_number: str = Field(..., description="Session number")
    opened_at: datetime = Field(..., description="Opening timestamp")
    operator_id: int = Field(..., description="Operator user ID")
    opening_balance: float = Field(..., description="Opening cash balance")
    is_open: bool = Field(default=True, description="Whether session is open")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "till_id": 1,
                "session_id": 10,
                "session_number": "1-1728317630",
                "opened_at": "2026-10-07T16:13:50.467Z",
                "operator_id": 1,
                "opening_balance": 5000.0,
                "is_open": True,
            }
        }


class TillSessionCloseResponse(BaseModel):
    """Response schema for successfully closed till session."""
    till_id: int = Field(..., description="Till ID")
    session_id: int = Field(..., description="Session ID")
    session_number: str = Field(..., description="Session number")
    closed_at: datetime = Field(..., description="Closing timestamp")
    closing_balance: float = Field(..., description="Closing cash balance")
    status: str = Field(default="CLOSED", description="Session status")
    notes: Optional[str] = Field(None, description="Closing notes")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "till_id": 1,
                "session_id": 10,
                "session_number": "1-1728317630",
                "closed_at": "2026-10-07T17:13:50.467Z",
                "closing_balance": 50000.0,
                "status": "CLOSED",
                "notes": "Balance verified",
            }
        }


class PaginatedTillResponse(BaseModel):
    """Response schema for paginated till list."""
    items: list[TillResponse] = Field(..., description="List of tills")
    total: int = Field(..., description="Total number of tills")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "organization_id": 1,
                        "location_id": 1,
                        "code": "TILL001",
                        "name": "Till 1",
                        "is_active": True,
                        "created_at": "2026-10-07T16:13:50.467Z",
                        "updated_at": "2026-10-07T16:13:50.467Z",
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 10,
            }
        }

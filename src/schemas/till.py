"""Pydantic schemas for till management and session operations."""
from datetime import datetime
from typing import Literal, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class TillCreate(BaseModel):
    """Request schema for creating a new till."""
    location_id: int = Field(..., description="Location ID where till is placed")
    code: str = Field(..., min_length=1, max_length=50, description="Till code/identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Till display name")

    class Config:
        json_schema_extra = {
            "example": {
                "location_id": 1,
                "code": "TILL001",
                "name": "Till 1",
            }
        }


class TillUpdate(BaseModel):
    """Fields that an administrator may edit on a till."""
    location_id: Optional[int] = None
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)


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
    user_id: Optional[int] = Field(
        default=None,
        description="Legacy field; operator identity is derived from the access token",
    )
    opening_balance: Optional[Decimal] = Field(
        Decimal("0.00"), ge=0, description="Opening cash balance in major units"
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
    session_id: int = Field(
        ..., gt=0, description="Open session that was reviewed and is being closed"
    )
    user_id: Optional[int] = Field(
        default=None,
        description="Legacy field; closing identity is derived from the access token",
    )
    closing_balance: Decimal = Field(
        ..., ge=0, description="Final cash balance in major units"
    )
    notes: Optional[str] = Field(None, description="Optional closing notes")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 10,
                "user_id": 1,
                "closing_balance": 500.0,
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
    currency_code: Optional[str] = Field(None, description="Session currency snapshot")

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
    currency_code: str = Field(..., description="Currency snapshot for the session")
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
    expected_closing_balance: float = Field(..., description="Expected cash at close")
    cash_variance: float = Field(..., description="Actual minus expected cash")
    currency_code: str = Field(..., description="Currency snapshot for the session")
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


class TillSessionHistoryItem(BaseModel):
    id: int
    till_id: int
    session_number: str
    operator_id: int
    opened_at: datetime
    closed_at: Optional[datetime] = None
    opening_balance: Decimal
    closing_balance: Optional[Decimal] = None
    expected_closing_balance: Optional[Decimal] = None
    cash_variance: Optional[Decimal] = None
    currency_code: Optional[str] = None
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedTillSessionHistory(BaseModel):
    items: list[TillSessionHistoryItem]
    total: int
    skip: int
    limit: int


class TillAssignmentsUpdate(BaseModel):
    employee_ids: list[int] = Field(..., description="Complete set of active employee assignments")


class TillAssignmentsResponse(BaseModel):
    till_id: int
    employee_ids: list[int]


class TillCashMovementCreate(BaseModel):
    operation_id: str = Field(..., min_length=1, max_length=100)
    movement_type: Literal["CASH_IN", "CASH_OUT"]
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    reason: str = Field(..., min_length=1, max_length=255)
    reference: Optional[str] = Field(None, max_length=255)


class TillCashMovementResponse(BaseModel):
    id: int
    organization_id: int
    till_id: int
    till_session_id: int
    movement_type: Literal["CASH_IN", "CASH_OUT"]
    amount: Decimal
    currency_code: str
    actor_user_id: int
    actor_employee_id: int
    operation_id: str
    reason: str
    reference: Optional[str] = None
    created_at: datetime

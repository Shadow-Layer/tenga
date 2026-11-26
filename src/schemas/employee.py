"""Pydantic schemas for organization employees."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class EmployeeFields(BaseModel):
    """Shared employee profile fields."""

    employee_number: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)

    @field_validator("employee_number", "full_name")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    model_config = ConfigDict(extra="forbid")


class EmployeeCreate(EmployeeFields):
    """Request schema for creating an employee without creating a login."""

    user_id: Optional[PositiveInt] = None
    location_ids: list[PositiveInt] = Field(default_factory=list)
    till_ids: list[PositiveInt] = Field(default_factory=list)


class EmployeeUpdate(BaseModel):
    """Partial employee update; supplied assignment lists replace access."""

    employee_number: Optional[str] = Field(None, min_length=1, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    user_id: Optional[PositiveInt] = None
    location_ids: Optional[list[PositiveInt]] = None
    till_ids: Optional[list[PositiveInt]] = None

    @field_validator("location_ids", "till_ids", mode="before")
    @classmethod
    def reject_null_assignments(cls, value):
        if value is None:
            raise ValueError("must be an array; use an empty array to revoke all assignments")
        return value

    @field_validator("employee_number", "full_name")
    @classmethod
    def reject_blank_values(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            raise ValueError("must not be null")
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    model_config = ConfigDict(extra="forbid")


class EmployeeResponse(BaseModel):
    """Employee profile and its current persisted assignments."""

    id: int
    organization_id: int
    employee_number: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    title: Optional[str]
    user_id: Optional[int]
    is_active: bool
    archived_at: Optional[datetime]
    location_ids: list[int]
    till_ids: list[int]
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    """Paginated employee list."""

    items: list[EmployeeResponse]
    total: int
    skip: int
    limit: int

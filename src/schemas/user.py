"""Pydantic schemas for user management."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Request schema for creating a user."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    password: str = Field(..., min_length=8, description="User password (plain text)")
    role: str = Field(default="operator", description="User role (operator, manager, admin)")


class UserResponse(BaseModel):
    """Response schema for a single user."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role (operator, manager, admin)")
    organization_id: int = Field(..., description="Organization ID")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response schema for user list."""
    items: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")


class LoginRequest(BaseModel):
    """Login request schema."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="Authenticated user details")


class CurrentUserResponse(BaseModel):
    """Current user info response."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role")
    organization_id: int = Field(..., description="Organization ID")
    is_active: bool = Field(..., description="Whether user is active")

    class Config:
        from_attributes = True


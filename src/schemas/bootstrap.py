"""Request and response models for first-install bootstrap."""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.schemas.organization import OrganizationCreate, OrganizationResponse
from src.schemas.user import UserResponse


class BootstrapOwnerCreate(BaseModel):
    """Credentials and profile for the first local administrator."""

    username: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def enforce_bcrypt_input_limit(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return password


class InstallationBootstrapRequest(BaseModel):
    """Initial organization and owner details for a fresh installation."""

    organization: OrganizationCreate
    owner: BootstrapOwnerCreate


class InstallationBootstrapResponse(BaseModel):
    """Created organization and owner, excluding all credentials."""

    organization: OrganizationResponse
    owner: UserResponse

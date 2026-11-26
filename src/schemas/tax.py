"""Pydantic contracts for configurable organization tax rules."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TaxRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    tax_inclusive: bool = False


class TaxRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    rate: Decimal | None = Field(None, ge=0, le=100, decimal_places=2)
    tax_inclusive: bool | None = None
    is_active: bool | None = None


class TaxRuleResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    rate: Decimal
    tax_inclusive: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

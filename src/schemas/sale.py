"""Pydantic schemas for sales endpoints."""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class SaleLineItem(BaseModel):
    """Line item in a sale request."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., ge=1, description="Quantity to sell")
    unit_price: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Quoted unit price snapshot, verified against the product",
    )
    tax_rate: Optional[Decimal] = Field(None, ge=0, description="Quoted tax-rate snapshot")
    tax_inclusive: Optional[bool] = Field(None, description="Quoted tax-inclusive snapshot")


class SaleCreate(BaseModel):
    """Request body for creating a sale."""
    till_id: int = Field(..., description="Till ID")
    cashier_id: Optional[int] = Field(
        default=None,
        description="Legacy field; cashier identity is derived from the access token",
    )
    payment_method: str = Field(..., description="Payment method (CASH, CARD, MOBILE, etc.)")
    amount_tendered: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Cash tendered; omitted for Paynow",
    )
    expected_total: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Server-verified checkout total snapshot",
    )
    items: List[SaleLineItem] = Field(..., min_items=1, description="Sale line items")
    is_offline: bool = Field(default=False, description="Whether sale is offline/pending")
    notes: Optional[str] = Field(default=None, description="Optional sale notes")
    till_session_id: int = Field(..., gt=0, description="Open till session for this sale")
    paynow_method: Optional[str] = Field(
        None, description="HOSTED or MOBILE_MONEY for Paynow"
    )
    phone_number: Optional[str] = Field(
        None, max_length=40, description="Mobile-money destination; never persisted"
    )
    idempotency_key: Optional[str] = Field(
        None, min_length=8, max_length=90, description="Stable client operation key"
    )


class SaleItemResponse(BaseModel):
    """Response model for sale line item with product details."""
    id: int = Field(..., description="Sale item ID")
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity sold")
    unit_price: float = Field(..., description="Unit price")
    discount_per_item: float = Field(..., description="Discount per item")
    total_price: float = Field(..., description="Total price (quantity * unit_price - discount)")
    tax_rule_id: Optional[int] = Field(None, description="Tax rule applied at sale time")
    tax_rate: Decimal = Field(..., description="Tax rate snapshot (percent)")
    tax_inclusive: bool = Field(..., description="Whether product price included tax")
    tax_amount: Decimal = Field(..., description="Tax amount rounded per line")

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    """Response model for a sale."""
    id: int = Field(..., description="Sale ID")
    organization_id: int = Field(..., description="Organization ID")
    till_id: int = Field(..., description="Till ID")
    till_session_id: Optional[int] = Field(None, description="Till session ID")
    currency_code: Optional[str] = Field(None, description="Currency snapshot")
    cashier_id: int = Field(..., description="Cashier user ID")
    total_amount: float = Field(..., description="Total sale amount")
    discount_amount: float = Field(..., description="Total discount")
    tax_amount: float = Field(..., description="Total tax")
    payment_method: str = Field(..., description="Payment method")
    amount_tendered: Decimal = Field(..., description="Cash tendered")
    change_given: Decimal = Field(..., description="Change returned")
    status: str = Field(..., description="Sale status (COMPLETED, PENDING, COMMITTED, etc.)")
    notes: Optional[str] = Field(None, description="Sale notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    sale_items: List[SaleItemResponse] = Field(default=[], description="Sale line items")

    class Config:
        from_attributes = True


class SaleListResponse(BaseModel):
    """Response model for paginated sales list."""
    items: List[SaleResponse] = Field(..., description="List of sales")
    total: int = Field(..., description="Total number of sales")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")


class SaleCommitRequest(BaseModel):
    """Request body for committing a pending sale."""
    user_id: Optional[int] = Field(
        default=None,
        description="Legacy field; commit identity is derived from the access token",
    )


class SaleCommitResponse(BaseModel):
    """Response model for committed sale."""
    id: int = Field(..., description="Sale ID")
    organization_id: int = Field(..., description="Organization ID")
    till_id: int = Field(..., description="Till ID")
    cashier_id: int = Field(..., description="Cashier user ID")
    total_amount: float = Field(..., description="Total sale amount")
    discount_amount: float = Field(..., description="Total discount")
    tax_amount: float = Field(..., description="Total tax")
    payment_method: str = Field(..., description="Payment method")
    amount_tendered: Decimal = Field(..., description="Cash tendered")
    change_given: Decimal = Field(..., description="Change returned")
    status: str = Field(..., description="Sale status after commit")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

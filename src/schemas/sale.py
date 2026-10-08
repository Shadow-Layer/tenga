"""Pydantic schemas for sales endpoints."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SaleLineItem(BaseModel):
    """Line item in a sale request."""
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., ge=1, description="Quantity to sell")
    unit_price: float = Field(..., ge=0, description="Unit price in currency")


class SaleCreate(BaseModel):
    """Request body for creating a sale."""
    till_id: int = Field(..., description="Till ID")
    cashier_id: int = Field(..., description="Cashier user ID")
    payment_method: str = Field(..., description="Payment method (CASH, CARD, MOBILE, etc.)")
    items: List[SaleLineItem] = Field(..., min_items=1, description="Sale line items")
    is_offline: bool = Field(default=False, description="Whether sale is offline/pending")
    notes: Optional[str] = Field(default=None, description="Optional sale notes")


class SaleItemResponse(BaseModel):
    """Response model for sale line item with product details."""
    id: int = Field(..., description="Sale item ID")
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity sold")
    unit_price: float = Field(..., description="Unit price")
    discount_per_item: float = Field(..., description="Discount per item")
    total_price: float = Field(..., description="Total price (quantity * unit_price - discount)")

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    """Response model for a sale."""
    id: int = Field(..., description="Sale ID")
    organization_id: int = Field(..., description="Organization ID")
    till_id: int = Field(..., description="Till ID")
    cashier_id: int = Field(..., description="Cashier user ID")
    total_amount: float = Field(..., description="Total sale amount")
    discount_amount: float = Field(..., description="Total discount")
    tax_amount: float = Field(..., description="Total tax")
    payment_method: str = Field(..., description="Payment method")
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
    user_id: int = Field(..., description="User ID performing the commit")


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
    status: str = Field(..., description="Sale status after commit")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

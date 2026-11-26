"""Product Pydantic schemas."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    sku: str = Field(..., min_length=1, max_length=100, description="Product SKU")
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    price: Decimal = Field(..., gt=0, description="Product selling price")
    cost: Optional[Decimal] = Field(None, ge=0, description="Product cost price")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode (optional)")
    organization_id: int = Field(..., description="Organization ID")
    unit_of_measure: str = Field("each", min_length=1, max_length=50)
    minimum_stock_level: int = Field(0, ge=0)
    tax_rule_id: Optional[int] = Field(
        None,
        description="Optional organization tax rule; omitted or null means no tax",
    )

    @field_validator("unit_of_measure")
    @classmethod
    def normalize_unit_of_measure(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Unit of measure cannot be empty.")
        return normalized


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    sku: Optional[str] = Field(None, min_length=1, max_length=100, description="Product SKU")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    price: Optional[Decimal] = Field(None, gt=0, description="Product selling price")
    cost: Optional[Decimal] = Field(None, ge=0, description="Product cost price")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode")
    unit_of_measure: Optional[str] = Field(None, min_length=1, max_length=50)
    minimum_stock_level: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    tax_rule_id: Optional[int] = Field(
        None,
        description="Optional tax rule; null explicitly removes tax assignment",
    )

    @field_validator("unit_of_measure")
    @classmethod
    def normalize_unit_of_measure(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Unit of measure cannot be empty.")
        return normalized


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int = Field(..., description="Product ID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Product category")
    price: Decimal = Field(..., description="Product selling price")
    cost: Optional[Decimal] = Field(None, description="Product cost price")
    barcode: Optional[str] = Field(None, description="Product barcode")
    unit_of_measure: str = Field(..., description="Inventory unit of measure")
    minimum_stock_level: int = Field(..., description="Low-stock threshold")
    tax_rule_id: Optional[int] = Field(None, description="Assigned tax rule ID")
    is_active: bool = Field(..., description="Whether product is active")
    is_active: bool = Field(..., description="Whether product is active")
    organization_id: int = Field(..., description="Organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""
    items: List[ProductResponse] = Field(..., description="List of products")
    total: int = Field(..., description="Total number of products")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items returned")

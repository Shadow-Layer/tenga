"""Product Pydantic schemas."""
from pydantic import BaseModel, Field
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
    cost: Optional[Decimal] = Field(None, gt=0, description="Product cost price")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode (optional)")
    organization_id: int = Field(..., description="Organization ID")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    sku: Optional[str] = Field(None, min_length=1, max_length=100, description="Product SKU")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    price: Optional[Decimal] = Field(None, gt=0, description="Product selling price")
    cost: Optional[Decimal] = Field(None, gt=0, description="Product cost price")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode")


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

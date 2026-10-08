"""Product Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class ProductCreate(BaseModel):
    """Schema for creating a product."""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    sku: str = Field(..., min_length=1, max_length=100, description="Product SKU (must be unique per organization)")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    category: Optional[str] = Field(None, max_length=100, description="Product category")
    price: Decimal = Field(..., gt=0, description="Selling price")
    cost: Optional[Decimal] = Field(None, ge=0, description="Cost price")
    organization_id: int = Field(..., description="Organization ID")


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Product category")
    price: Decimal = Field(..., description="Selling price")
    cost: Optional[Decimal] = Field(None, description="Cost price")
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

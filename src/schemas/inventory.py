"""Inventory Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class StockItem(BaseModel):
    """Stock information for a single product at a location."""
    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., description="Current stock quantity")
    last_movement_date: Optional[datetime] = Field(None, description="Last movement timestamp")


class StockResponse(BaseModel):
    """Response for current stock at a location."""
    location_id: int = Field(..., description="Location ID")
    items: List[StockItem] = Field(..., description="Stock items")
    total_items: int = Field(..., description="Total number of items in stock")


class InventoryMovement(BaseModel):
    """Inventory movement record."""
    id: int = Field(..., description="Movement ID")
    product_id: int = Field(..., description="Product ID")
    location_id: int = Field(..., description="Location ID")
    quantity: int = Field(..., description="Quantity moved (positive or negative)")
    reason: str = Field(..., description="Movement reason")
    recorded_by_id: int = Field(..., description="User ID who recorded the movement")
    created_at: datetime = Field(..., description="Movement timestamp")
    
    class Config:
        from_attributes = True


class MovementListResponse(BaseModel):
    """Response for paginated inventory movements."""
    items: List[InventoryMovement] = Field(..., description="List of movements")
    total: int = Field(..., description="Total number of movements")
    skip: int = Field(default=0, description="Number of items skipped")
    limit: int = Field(default=20, description="Number of items returned")


class MovementDetailResponse(BaseModel):
    """Detailed inventory movement record with product and user info."""
    id: int = Field(..., description="Movement ID")
    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    location_id: int = Field(..., description="Location ID")
    quantity: int = Field(..., description="Quantity moved")
    reason: str = Field(..., description="Movement reason")
    recorded_by_id: int = Field(..., description="User ID who recorded the movement")
    user_name: str = Field(..., description="Name of user who recorded movement")
    created_at: datetime = Field(..., description="Movement timestamp")
    
    class Config:
        from_attributes = True


class AdjustmentCreate(BaseModel):
    """Request for manual inventory adjustment."""
    product_id: int = Field(..., gt=0, description="Product ID")
    location_id: int = Field(..., gt=0, description="Location ID")
    quantity: int = Field(..., description="Adjustment quantity (positive or negative)")
    reason: str = Field(..., min_length=1, description="Adjustment reason (PHYSICAL_COUNT_DISCREPANCY, DAMAGE, SHRINKAGE)")
    recorded_by_id: int = Field(..., gt=0, description="User ID recording the adjustment")
    note: Optional[str] = Field(None, description="Optional adjustment notes")


class Discrepancy(BaseModel):
    """Inventory discrepancy at a location."""
    product_id: int = Field(..., description="Product ID")
    location_id: int = Field(..., description="Location ID")
    physical_count: int = Field(..., description="Physical count from inventory")
    ledger_count: int = Field(..., description="Ledger count from system")
    discrepancy: int = Field(..., description="Difference (physical - ledger)")


class DiscrepancyListResponse(BaseModel):
    """Response for list of discrepancies at a location."""
    items: List[Discrepancy] = Field(..., description="List of discrepancies")
    location_id: int = Field(..., description="Location ID")

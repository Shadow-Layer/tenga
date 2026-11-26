"""Inventory Pydantic schemas."""
from decimal import Decimal
from pydantic import BaseModel, Field, condecimal, conint, constr, field_validator
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
    to_location_id: Optional[int] = Field(None, description="Transfer destination location")
    movement_type: str = Field(..., description="Ledger movement type")
    quantity: int = Field(..., description="Quantity moved (positive or negative)")
    reason: str = Field(..., description="Movement reason")
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    currency_code: Optional[str] = None
    device_id: Optional[str] = None
    device_local_id: Optional[str] = None
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
    """Request for manual inventory adjustment.
    
    CRITICAL: recorded_by_id and organization_id are NOT sent by client.
    These are derived from the authenticated JWT token by the backend.
    The backend establishes trusted identity and tenancy from authentication.
    """
    product_id: int = Field(..., gt=0, description="Product ID")
    location_id: int = Field(..., gt=0, description="Location ID")
    quantity: int = Field(..., description="Adjustment quantity (positive or negative)")
    reason: str = Field(..., description="Adjustment reason (PHYSICAL_COUNT_DISCREPANCY, DAMAGE, SHRINKAGE, ADJUSTMENT)")
    note: Optional[str] = Field(None, description="Optional adjustment notes")

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_nonzero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Adjustment quantity must be non-zero")
        return value


class StockReceiptCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    location_id: int = Field(..., gt=0)
    quantity: conint(gt=0)
    unit_cost: Optional[condecimal(ge=0, max_digits=12, decimal_places=2)] = None
    reason: constr(min_length=1, max_length=100) = "RECEIPT"
    device_id: Optional[constr(min_length=1, max_length=100)] = None
    device_local_id: Optional[constr(min_length=1, max_length=100)] = None


class OpeningStockCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    location_id: int = Field(..., gt=0)
    quantity: int
    unit_cost: Optional[condecimal(ge=0, max_digits=12, decimal_places=2)] = None
    reason: constr(min_length=1, max_length=100) = "OPENING_BALANCE"
    device_id: Optional[constr(min_length=1, max_length=100)] = None
    device_local_id: Optional[constr(min_length=1, max_length=100)] = None


class StockIssueCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    location_id: int = Field(..., gt=0)
    quantity: conint(gt=0)
    reason: constr(min_length=1, max_length=100)
    device_id: Optional[constr(min_length=1, max_length=100)] = None
    device_local_id: Optional[constr(min_length=1, max_length=100)] = None


class TransferLineCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: conint(gt=0)


class StockTransferCreate(BaseModel):
    source_location_id: int = Field(..., gt=0)
    destination_location_id: int = Field(..., gt=0)
    lines: List[TransferLineCreate] = Field(..., min_length=1)
    reason: constr(min_length=1, max_length=100) = "TRANSFER"
    device_id: Optional[constr(min_length=1, max_length=100)] = None
    device_local_id: Optional[constr(min_length=1, max_length=100)] = None


class InventoryCountLineInput(BaseModel):
    product_id: int = Field(..., gt=0)
    observed_quantity: Optional[conint(ge=0)] = None


class InventoryCountCreate(BaseModel):
    location_id: int = Field(..., gt=0)
    lines: List[InventoryCountLineInput] = Field(..., min_length=1)
    notes: Optional[str] = None


class InventoryCountObservationUpdate(BaseModel):
    lines: List[InventoryCountLineInput] = Field(..., min_length=1)


class InventoryCountReconcileRequest(BaseModel):
    expected_observations: List[InventoryCountLineInput] = Field(..., min_length=1)


class InventoryCountLineResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    expected_quantity: int
    observed_quantity: Optional[int]
    difference: Optional[int]
    reconciled_movement_id: Optional[int]


class InventoryCountResponse(BaseModel):
    id: int
    location_id: int
    status: str
    notes: Optional[str]
    created_by_id: int
    reconciled_by_id: Optional[int]
    started_at: datetime
    reconciled_at: Optional[datetime]
    lines: List[InventoryCountLineResponse]


class InventoryTransferLineResponse(BaseModel):
    product_id: int
    quantity: int


class InventoryTransferResponse(BaseModel):
    id: int
    source_location_id: int
    destination_location_id: int
    reason: str
    status: str
    created_by_id: int
    device_id: Optional[str]
    device_local_id: Optional[str]
    created_at: datetime
    lines: List[InventoryTransferLineResponse]


class InventoryValueItem(BaseModel):
    product_id: int
    product_name: str
    location_id: int
    quantity: int
    weighted_average_cost: Optional[Decimal]
    inventory_value: Optional[Decimal]
    currency_code: Optional[str]


class InventoryValueReport(BaseModel):
    items: List[InventoryValueItem]
    currency_code: Optional[str]
    total_value: Optional[Decimal]
    valuation_complete: bool


class LowStockItem(BaseModel):
    product_id: int
    product_name: str
    location_id: int
    quantity: int
    minimum_stock_level: int


class LowStockReport(BaseModel):
    items: List[LowStockItem]
    total_items: int


class LocationInventoryItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    weighted_average_cost: Optional[Decimal]
    inventory_value: Optional[Decimal]
    currency_code: Optional[str]


class LocationInventoryReport(BaseModel):
    location_id: int
    items: List[LocationInventoryItem]
    total_items: int
    currency_code: Optional[str]
    total_value: Optional[Decimal]
    valuation_complete: bool


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

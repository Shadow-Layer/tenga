"""Fiscal submission request formatting and validation."""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class PaymentMethod(str, Enum):
    """Supported payment methods for fiscal submission."""
    CASH = "CASH"
    CARD = "CARD"
    MOBILE_MONEY = "MOBILE_MONEY"


class FiscalLineItem(BaseModel):
    """Line item in fiscal submission."""
    product_name: str = Field(..., max_length=50, description="Product name")
    quantity: Decimal = Field(..., description="Quantity (2 decimal places)")
    unit_price: Decimal = Field(..., description="Unit price (4 decimal places)")
    total_price: Decimal = Field(..., description="Total price (4 decimal places)")
    tax_rate: Decimal = Field(..., description="Tax rate percentage")
    tax_amount: Decimal = Field(..., description="Tax amount (4 decimal places)")
    
    model_config = {"json_encoders": {Decimal: lambda v: str(v)}}
    
    @field_validator('product_name')
    @classmethod
    def product_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty")
        return v.strip()
    
    @field_validator('quantity', 'unit_price', 'total_price', 'tax_rate', 'tax_amount', mode='before')
    @classmethod
    def validate_decimal(cls, v):
        """Convert to Decimal and validate."""
        if v is None:
            raise ValueError("Decimal value is required")
        try:
            return Decimal(str(v))
        except Exception:
            raise ValueError(f"Invalid decimal value: {v}")
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity_places(cls, v):
        """Validate quantity decimal places."""
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        quantized = v.quantize(Decimal('0.01'))
        if v != quantized:
            raise ValueError(
                f"Invalid 'quantity': expected decimal with ≤2 decimals, got '{v}'"
            )
        return v
    
    @field_validator('unit_price', 'total_price', 'tax_amount')
    @classmethod
    def validate_price_places(cls, v):
        """Validate price decimal places."""
        if v < 0:
            raise ValueError("Price cannot be negative")
        quantized = v.quantize(Decimal('0.0001'))
        if v != quantized:
            raise ValueError(
                f"Invalid price: expected decimal with ≤4 decimals, got '{v}'"
            )
        return v
    
    @field_validator('tax_rate')
    @classmethod
    def validate_tax_rate(cls, v):
        """Tax rate should be percentage (0-100)."""
        if v < 0 or v > 100:
            raise ValueError("Tax rate must be between 0 and 100")
        return v


class FiscalSubmissionRequest(BaseModel):
    """Fiscal submission request to ZIMRA."""
    sale_id: str = Field(..., max_length=36, description="Sale ID")
    device_id: str = Field(..., max_length=50, description="ZIMRA device ID")
    timestamp: datetime = Field(..., description="Submission timestamp")
    items: List[FiscalLineItem] = Field(..., min_length=1, description="Line items")
    subtotal: Decimal = Field(..., description="Subtotal (4 decimal places)")
    tax_amount: Decimal = Field(..., description="Tax amount (4 decimal places)")
    total: Decimal = Field(..., description="Total amount (4 decimal places)")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    customer_id: Optional[str] = Field(None, max_length=36, description="Customer ID")
    idempotency_key: str = Field(..., max_length=100, description="Unique idempotency key")
    
    model_config = {
        "json_encoders": {
            Decimal: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
    }
    
    @field_validator('sale_id', 'device_id', 'idempotency_key')
    @classmethod
    def validate_string_fields(cls, v):
        """Validate string fields."""
        if not v or not str(v).strip():
            raise ValueError(f"Field cannot be empty")
        return str(v).strip()
    
    @field_validator('subtotal', 'tax_amount', 'total', mode='before')
    @classmethod
    def validate_totals_decimal(cls, v):
        """Convert totals to Decimal."""
        if v is None:
            raise ValueError("Total value is required")
        try:
            return Decimal(str(v))
        except Exception:
            raise ValueError(f"Invalid decimal value: {v}")
    
    @field_validator('subtotal')
    @classmethod
    def validate_subtotal_places(cls, v):
        """Validate subtotal decimal places."""
        if v < 0:
            raise ValueError("Subtotal cannot be negative")
        quantized = v.quantize(Decimal('0.0001'))
        if v != quantized:
            raise ValueError(
                f"Invalid 'subtotal': expected decimal with ≤4 decimals, got '{v}'"
            )
        return v
    
    @field_validator('tax_amount')
    @classmethod
    def validate_tax_amount_places(cls, v):
        """Validate tax amount decimal places."""
        if v < 0:
            raise ValueError("Tax amount cannot be negative")
        quantized = v.quantize(Decimal('0.0001'))
        if v != quantized:
            raise ValueError(
                f"Invalid 'tax_amount': expected decimal with ≤4 decimals, got '{v}'"
            )
        return v
    
    @field_validator('total')
    @classmethod
    def validate_total_places(cls, v):
        """Validate total decimal places."""
        if v < 0:
            raise ValueError("Total cannot be negative")
        quantized = v.quantize(Decimal('0.0001'))
        if v != quantized:
            raise ValueError(
                f"Invalid 'total': expected decimal with ≤4 decimals, got '{v}'"
            )
        return v
    
    @model_validator(mode='after')
    def validate_totals_consistency(self):
        """Validate that totals are consistent."""
        if not self.items:
            return self
        
        # Calculate sum of line item totals
        items_total = sum(item.total_price for item in self.items)
        
        # Calculate sum of tax amounts
        items_tax = sum(item.tax_amount for item in self.items)
        
        # Tolerance for floating-point comparisons
        tolerance = Decimal('0.01')
        
        # Validate subtotal matches items
        if abs(items_total - self.subtotal) > tolerance:
            raise ValueError(
                f"Validation failed: sum of line items ({items_total}) != subtotal ({self.subtotal})"
            )
        
        # Validate tax matches items
        if abs(items_tax - self.tax_amount) > tolerance:
            raise ValueError(
                f"Validation failed: sum of line item taxes ({items_tax}) != tax_amount ({self.tax_amount})"
            )
        
        # Validate total = subtotal + tax
        expected_total = self.subtotal + self.tax_amount
        if abs(expected_total - self.total) > tolerance:
            raise ValueError(
                f"Validation failed: subtotal ({self.subtotal}) + tax ({self.tax_amount}) != total ({self.total})"
            )
        
        return self


class FiscalFormatter:
    """Format and validate fiscal submission requests."""
    
    @staticmethod
    def format_request(
        sale_id: str,
        device_id: str,
        items: List[Dict[str, Any]],
        subtotal: Decimal,
        tax_amount: Decimal,
        total: Decimal,
        payment_method: str,
        idempotency_key: str,
        customer_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> FiscalSubmissionRequest:
        """
        Format and validate fiscal submission request.
        
        Args:
            sale_id: Sale ID
            device_id: ZIMRA device ID
            items: Line items
            subtotal: Subtotal amount
            tax_amount: Tax amount
            total: Total amount
            payment_method: Payment method (CASH, CARD, MOBILE_MONEY)
            idempotency_key: Unique key for idempotency
            customer_id: Optional customer ID
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Validated FiscalSubmissionRequest
            
        Raises:
            ValueError: If validation fails with descriptive error message
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Convert items to FiscalLineItem objects
        fiscal_items = []
        for item in items:
            fiscal_items.append(FiscalLineItem(**item))
        
        # Create and validate request
        request = FiscalSubmissionRequest(
            sale_id=sale_id,
            device_id=device_id,
            timestamp=timestamp,
            items=fiscal_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            payment_method=payment_method,
            customer_id=customer_id,
            idempotency_key=idempotency_key
        )
        
        return request
    
    @staticmethod
    def to_dict(request: FiscalSubmissionRequest) -> Dict[str, Any]:
        """Convert request to dictionary for API submission."""
        return request.model_dump(by_alias=False)


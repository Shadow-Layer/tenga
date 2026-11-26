"""Paynow API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PaynowAttemptResponse(BaseModel):
    id: int
    sale_id: int
    merchant_reference: str
    provider_reference: Optional[str] = None
    payment_method: str
    amount: Decimal
    currency_code: str
    status: str
    redirect_url: Optional[str] = None
    verified_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    sale_status: str

    class Config:
        from_attributes = True


class PaynowRetryRequest(BaseModel):
    phone_number: Optional[str] = None

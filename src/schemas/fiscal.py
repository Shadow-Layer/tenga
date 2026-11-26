"""Fiscal submission API schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FiscalSubmissionResponse(BaseModel):
    id: int
    sale_id: int
    attempt_number: int
    status: str
    request_reference: str
    fiscal_number: Optional[str] = None
    error_message: Optional[str] = None
    submitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FiscalStatusResponse(BaseModel):
    sale_id: int
    fiscal_status: str
    fiscal_number: Optional[str] = None
    submissions: List[FiscalSubmissionResponse]


class FiscalSubmitRequest(BaseModel):
    retry_failed: bool = False

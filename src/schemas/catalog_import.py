"""Schemas for catalog CSV import, export, and history endpoints."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CSVImportRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)


class CSVRowError(BaseModel):
    row_number: int
    field: str
    message: str


class CSVImportPreview(BaseModel):
    valid: bool
    already_imported: bool = False
    row_count: int
    valid_count: int
    errors: list[CSVRowError]
    truncated_errors: int = 0
    rows: list[dict[str, Any]]
    truncated_rows: int = 0


class CSVImportCommitResult(BaseModel):
    batch_id: int
    record_count: int
    already_imported: bool


class CatalogImportHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_type: str
    content_sha256: str
    row_count: int
    created_by_id: int
    created_at: datetime


class CatalogImportHistory(BaseModel):
    items: list[CatalogImportHistoryItem]
    total: int
    skip: int
    limit: int

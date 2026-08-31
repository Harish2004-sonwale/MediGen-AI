"""Pydantic Schemas for FHIR Bulk Data Export ($export) and Asynchronous Status."""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BulkExportRequest(BaseModel):
    export_type: str = Field(default="PATIENT", description="Export level: PATIENT, GROUP, or SYSTEM")
    since: Optional[datetime] = Field(default=None, description="Only include resources modified since timestamp")
    types: Optional[List[str]] = Field(default=None, description="Resource types to export (e.g. ['Patient', 'Observation', 'Condition'])")
    group_id: Optional[str] = Field(default=None, description="Target Group ID for group-level export")


class BulkExportFileItem(BaseModel):
    type: str
    url: str
    count: Optional[int] = None


class BulkExportStatusResponse(BaseModel):
    transaction_time: datetime
    request_url: str
    requires_access_token: bool = True
    output: List[BulkExportFileItem] = []
    error: List[dict[str, Any]] = []
    progress: Optional[str] = None


class BulkExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    facility_id: Optional[str] = None
    user_id: int
    export_type: str
    status: str
    output_urls_json: Optional[List[dict[str, Any]]] = None
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

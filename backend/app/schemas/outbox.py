"""Pydantic Schemas for Outbox Monitoring and DLQ Replay."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class OutboxEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    facility_id: Optional[str] = None
    payload_json: dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    retry_after: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime


class OutboxReplayRequest(BaseModel):
    event_ids: Optional[list[str]] = None


class OutboxReplayResponse(BaseModel):
    replayed_count: int
    message: str


class OutboxMetricsResponse(BaseModel):
    pending: int
    published: int
    failed: int
    dead_letter: int
    total: int

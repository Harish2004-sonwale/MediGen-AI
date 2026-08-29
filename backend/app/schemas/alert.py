"""Pydantic schemas for Clinical Decision Support Alerts & Lifecycle Management.

Phase 9.0.9: Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertSeverity(str, Enum):
    """Standard clinical alert severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Lifecycle state of a clinical decision support alert."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class AlertAcknowledgeRequest(BaseModel):
    """Clinician acknowledgement request."""

    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional clinician review remarks",
    )


class AlertDismissRequest(BaseModel):
    """Clinician dismissal request with mandatory clinical rationale."""

    reason: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Mandatory clinical justification for alert dismissal",
    )


class ClinicalAlertResponse(BaseModel):
    """Full representation of a persistent clinical decision support alert."""

    id: int
    alert_id: str
    patient_id: int
    encounter_id: Optional[int]
    reading_id: Optional[int]
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    explanation: str
    parameters_json: Optional[dict[str, Any]]
    recurrence_count: int
    acknowledged_by_user_id: Optional[int]
    acknowledged_at: Optional[datetime]
    dismissal_reason: Optional[str]
    last_triggered_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicalAlertListResponse(BaseModel):
    """List envelope for clinical decision support alerts."""

    items: list[ClinicalAlertResponse]
    total: int

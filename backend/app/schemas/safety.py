"""Schemas for Clinical Decision Support (CDS) and Safety Alerts.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import RAGCitation


class SafetySeverity(str, Enum):
    """Clinical safety alert severity levels."""

    INFO = "INFO"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyAlertType(str, Enum):
    """Categories of clinical safety alerts."""

    MEDICATION_DUPLICATE = "medication_duplicate"
    ALLERGY_WARNING = "allergy_warning"
    DRUG_INTERACTION = "drug_interaction"
    CONTRAINDICATION = "contraindication"
    DOSING_WARNING = "dosing_warning"


class ClinicalSafetyAlert(BaseModel):
    """Structured decision support alert."""

    alert_id: str = Field(..., description="Unique alert identifier (e.g. ALT-20260828-A1B2)")
    patient_id: str = Field(..., description="Target patient identifier")
    alert_type: SafetyAlertType = Field(..., description="Classification of the alert")
    severity: SafetySeverity = Field(..., description="Severity classification")
    title: str = Field(..., description="Short descriptive title of the alert")
    explanation: str = Field(..., description="Detailed clinical explanation of the detected conflict")
    medications: list[str] = Field(default_factory=list, description="Involved medication names")
    source_references: list[str] = Field(default_factory=list, description="Clinical evidence or guidance references")
    generated_at: datetime = Field(..., description="Timestamp when the alert was generated")
    provider: str = Field(..., description="Originating provider (e.g. MockCDS, RxNormCDS, RuleEngine)")
    requires_clinician_review: bool = Field(True, description="Strict indicator that clinician review is required")
    citations: list[RAGCitation] = Field(default_factory=list, description="Patient record citations establishing the alert")

    model_config = ConfigDict(from_attributes=True)


class SafetyCheckRequest(BaseModel):
    """Request payload to run safety analysis against patient records and candidate medications."""

    candidate_medications: Optional[list[str]] = Field(
        default=None,
        description="Optional list of new/candidate medications to check against patient history",
    )
    active_conditions: Optional[list[str]] = Field(
        default=None,
        description="Optional additional active diagnoses/conditions to evaluate",
    )


class ClinicalSafetyReport(BaseModel):
    """Comprehensive clinical decision support evaluation report."""

    patient_id: str = Field(..., description="Target patient identifier")
    alerts: list[ClinicalSafetyAlert] = Field(..., description="List of generated safety alerts")
    checked_items: int = Field(..., description="Total clinical items (medications, allergies, conditions) evaluated")
    safe_to_proceed: bool = Field(
        ...,
        description="True if no CRITICAL or HIGH severity alerts detected, False otherwise",
    )
    summary: str = Field(..., description="High-level summary of safety findings")
    disclaimer: str = Field(
        default="Decision-support alert only. Clinician review required. Does not replace professional medical judgment.",
        description="Mandatory clinical decision support disclaimer",
    )
    generated_at: datetime = Field(..., description="Timestamp when report was generated")

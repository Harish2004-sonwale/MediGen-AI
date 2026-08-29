"""Schemas for Multi-Modal Medical Diagnostics and Imaging Support.

Phase 9.0.7: Advanced Multi-Modal Medical Diagnostics & Imaging Support.
Defines schemas for:
- Medical modalities & body sites
- Media status lifecycle
- Structured imaging findings and confidence scoring
- Clinician review and confirmation signoff
- Upload request and API response models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class MediaModality(str, Enum):
    """Supported clinical imaging modalities."""

    XRAY_CHEST = "xray_chest"
    CT_SCAN = "ct_scan"
    MRI = "mri"
    ULTRASOUND = "ultrasound"
    DERMATOLOGY = "dermatology"
    PATHOLOGY = "pathology"
    OTHER = "other"


class MediaBodySite(str, Enum):
    """Target anatomical body sites."""

    CHEST = "chest"
    BRAIN = "brain"
    ABDOMEN = "abdomen"
    PELVIS = "pelvis"
    EXTREMITY = "extremity"
    SPINE = "spine"
    SKIN = "skin"
    WHOLE_BODY = "whole_body"
    OTHER = "other"


class MediaStatus(str, Enum):
    """Processing and review status lifecycle for medical media."""

    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    REVIEWED = "reviewed"
    FAILED = "failed"


class ImagingFindingItem(BaseModel):
    """Individual anatomical or pathological observation."""

    observation: str = Field(..., description="Description of the finding")
    anatomical_region: str = Field(..., description="Target anatomical structure")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    is_abnormal: bool = Field(False, description="Whether the finding indicates an abnormality")
    severity: Optional[str] = Field(default=None, description="Optional severity classification")


class StructuredImagingFinding(BaseModel):
    """Complete structured imaging analysis payload."""

    modality: MediaModality = Field(..., description="Evaluated imaging modality")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall finding confidence ratio")
    primary_observation: str = Field(..., description="High-level primary clinical observation")
    findings: list[ImagingFindingItem] = Field(default_factory=list, description="Granular observations")
    differential_notes: list[str] = Field(default_factory=list, description="Differential considerations for clinician review")
    disclaimer: str = Field(
        default="AI clinical decision support observation only. Must be validated by a certified radiologist/clinician. Does not constitute a definitive medical diagnosis.",
        description="Mandatory clinical safety disclaimer",
    )


class ClinicianReviewRequest(BaseModel):
    """Payload for clinician verification and signoff of AI findings."""

    clinician_confirmed: bool = Field(..., description="Clinician agreement with AI findings")
    clinician_notes: Optional[str] = Field(default=None, max_length=2000, description="Clinician review remarks or differential notes")
    override_diagnosis: Optional[str] = Field(default=None, max_length=500, description="Optional diagnostic correction or override")


class DiagnosticMediaResponse(BaseModel):
    """Public response representation of a diagnostic media record."""

    id: int
    media_id: str
    patient_id: int
    uploader_user_id: Optional[int] = None
    encounter_id: Optional[int] = None
    title: str
    modality: MediaModality
    body_site: Optional[MediaBodySite] = None
    original_filename: str
    file_size_bytes: int
    mime_type: str
    status: MediaStatus
    confidence_score: Optional[float] = None
    findings_summary: Optional[str] = None
    structured_findings: Optional[dict[str, Any]] = None
    anomalies_detected: Optional[list[dict[str, Any]]] = None
    requires_clinician_review: bool = True
    clinician_confirmed: bool = False
    clinician_notes: Optional[str] = None
    created_at: datetime
    analyzed_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiagnosticMediaListResponse(BaseModel):
    """Paginated collection of diagnostic media records."""

    items: list[DiagnosticMediaResponse]
    total: int

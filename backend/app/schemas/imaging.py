"""Pydantic schemas for Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.

Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImagingModality(str, Enum):
    """Supported imaging modalities."""

    XRAY = "XRAY"
    CT = "CT"
    MRI = "MRI"
    ULTRASOUND = "ULTRASOUND"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    PET_CT = "PET_CT"
    ECHOCARDIOGRAPHY = "ECHOCARDIOGRAPHY"
    OTHER = "OTHER"


class ImagingBodySite(str, Enum):
    """Anatomical imaging regions."""

    CHEST = "CHEST"
    ABDOMEN = "ABDOMEN"
    PELVIS = "PELVIS"
    HEAD_BRAIN = "HEAD_BRAIN"
    SPINE = "SPINE"
    EXTREMITY = "EXTREMITY"
    CARDIAC = "CARDIAC"
    BREAST = "BREAST"
    NECK = "NECK"
    OTHER = "OTHER"


class ImagingStudyStatus(str, Enum):
    """Clinical imaging study lifecycle status."""

    ORDERED = "ORDERED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PRELIMINARY = "PRELIMINARY"
    FINAL = "FINAL"
    CANCELLED = "CANCELLED"


class ImagingFindingType(str, Enum):
    """Categorization of image findings."""

    NORMAL_APPEARANCE = "NORMAL_APPEARANCE"
    POSSIBLE_NODULE = "POSSIBLE_NODULE"
    POSSIBLE_FRACTURE = "POSSIBLE_FRACTURE"
    POSSIBLE_PNEUMONIA = "POSSIBLE_PNEUMONIA"
    POSSIBLE_EFFUSION = "POSSIBLE_EFFUSION"
    POSSIBLE_HEMORRHAGE = "POSSIBLE_HEMORRHAGE"
    POSSIBLE_MASS = "POSSIBLE_MASS"
    OTHER_ABNORMALITY = "OTHER_ABNORMALITY"


class FindingLaterality(str, Enum):
    """Anatomical laterality of the finding."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BILATERAL = "BILATERAL"
    MIDLINE = "MIDLINE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FindingSeverity(str, Enum):
    """Clinical severity or urgency of the finding."""

    NORMAL = "NORMAL"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class FindingNature(str, Enum):
    """Epistemological nature of finding."""

    OBSERVED_FACT = "OBSERVED_FACT"
    AI_GENERATED_FINDING = "AI_GENERATED_FINDING"
    CLINICIAN_CONFIRMED_FINDING = "CLINICIAN_CONFIRMED_FINDING"


class FindingReviewStatus(str, Enum):
    """Clinician review status for an AI-assisted finding."""

    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AMENDED = "amended"


class ReportStatus(str, Enum):
    """Radiology report governance lifecycle."""

    DRAFT = "DRAFT"
    AI_ASSISTED = "AI_ASSISTED"
    RADIOLOGIST_REVIEW = "RADIOLOGIST_REVIEW"
    FINALIZED = "FINALIZED"
    AMENDED = "AMENDED"


# =============================================================================
# Imaging Asset Schemas
# =============================================================================

class ImagingAssetCreate(BaseModel):
    """Payload to register an image asset or series within a study."""

    series_instance_uid: Optional[str] = None
    sop_instance_uid: Optional[str] = None
    series_number: Optional[int] = 1
    instance_number: Optional[int] = 1
    series_description: Optional[str] = None
    modality: ImagingModality = ImagingModality.XRAY
    body_site: Optional[ImagingBodySite] = None
    mime_type: str = "image/png"
    file_size_bytes: int = 0
    storage_path: str
    thumbnail_storage_path: Optional[str] = None
    image_dimensions: Optional[dict[str, Any]] = None
    dicom_metadata_json: Optional[dict[str, Any]] = None


class ImagingAssetResponse(BaseModel):
    """Response schema for an imaging asset."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: str
    study_id: int
    series_instance_uid: Optional[str] = None
    sop_instance_uid: Optional[str] = None
    series_number: Optional[int] = 1
    instance_number: Optional[int] = 1
    series_description: Optional[str] = None
    modality: str
    body_site: Optional[str] = None
    mime_type: str
    file_size_bytes: int
    storage_path: str
    thumbnail_storage_path: Optional[str] = None
    image_dimensions: Optional[dict[str, Any]] = None
    dicom_metadata_json: Optional[dict[str, Any]] = None
    provenance_hash: str
    created_at: datetime


class ImagingAssetListResponse(BaseModel):
    """List response for imaging assets."""

    items: list[ImagingAssetResponse]
    total: int


# =============================================================================
# Imaging Finding Schemas
# =============================================================================

class ImagingFindingResponse(BaseModel):
    """Structured response for an image finding."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: str
    study_id: int
    asset_id: Optional[int] = None
    patient_id: int
    finding_type: str
    anatomical_location: str
    laterality: str
    severity: str
    confidence_score: float
    is_critical: bool
    finding_nature: str
    description: str
    recommendation: str
    bounding_box_json: Optional[dict[str, Any]] = None
    clinician_review_status: str
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    provenance_hash: str
    created_at: datetime


class ImagingFindingListResponse(BaseModel):
    """List response for imaging findings."""

    items: list[ImagingFindingResponse]
    total: int


class FindingReviewRequest(BaseModel):
    """Clinician review action for an individual finding."""

    review_status: FindingReviewStatus = FindingReviewStatus.CONFIRMED
    review_notes: Optional[str] = None


# =============================================================================
# Imaging Study Schemas
# =============================================================================

class ImagingStudyCreate(BaseModel):
    """Payload to create or ingest an Imaging Study."""

    patient_id: str = Field(..., description="Patient business identifier or DB ID")
    encounter_id: Optional[int] = None
    order_id: Optional[int] = None
    modality: ImagingModality = ImagingModality.XRAY
    body_site: ImagingBodySite = ImagingBodySite.CHEST
    study_description: str = Field(..., min_length=3, max_length=255)
    accession_number: Optional[str] = None
    study_datetime: Optional[datetime] = None
    performing_department: Optional[str] = "Radiology & Diagnostic Imaging"
    referring_provider: Optional[str] = None
    status: ImagingStudyStatus = ImagingStudyStatus.ORDERED
    source: Optional[str] = "PACS_IMPORT"
    external_identifier: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ImagingStudyUpdate(BaseModel):
    """Payload to update an Imaging Study."""

    study_description: Optional[str] = None
    status: Optional[ImagingStudyStatus] = None
    performing_department: Optional[str] = None
    referring_provider: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None


class ImagingStudyResponse(BaseModel):
    """Response schema for an Imaging Study."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    study_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    order_id: Optional[int] = None
    modality: str
    body_site: str
    study_description: str
    accession_number: str
    study_datetime: datetime
    performing_department: str
    referring_provider: Optional[str] = None
    status: str
    source: str
    external_identifier: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    provenance_hash: str
    created_at: datetime
    updated_at: datetime

    assets_count: Optional[int] = 0
    findings_count: Optional[int] = 0
    reports_count: Optional[int] = 0
    has_critical_findings: Optional[bool] = False


class ImagingStudyListResponse(BaseModel):
    """List response for imaging studies."""

    items: list[ImagingStudyResponse]
    total: int


# =============================================================================
# Radiology Report Schemas
# =============================================================================

class RadiologyReportCreate(BaseModel):
    """Payload to draft a structured radiology report."""

    clinical_indication: str
    technique: str
    comparison_studies: Optional[str] = "None available."
    findings: str
    impression: str
    recommendations: str
    critical_findings_summary: Optional[str] = None
    is_critical: Optional[bool] = False


class RadiologyReportUpdate(BaseModel):
    """Payload to edit a draft radiology report."""

    clinical_indication: Optional[str] = None
    technique: Optional[str] = None
    comparison_studies: Optional[str] = None
    findings: Optional[str] = None
    impression: Optional[str] = None
    recommendations: Optional[str] = None
    critical_findings_summary: Optional[str] = None
    is_critical: Optional[bool] = None


class ReportFinalizeRequest(BaseModel):
    """Clinician sign-off action to finalize a report."""

    signature_notes: Optional[str] = None
    confirm_accuracy: bool = Field(True, description="Clinician attestation confirming review")


class ReportAmendRequest(BaseModel):
    """Clinician action to create an amended report version."""

    amendment_reason: str = Field(..., min_length=5, description="Clinical reason for report amendment")
    amended_findings: Optional[str] = None
    amended_impression: Optional[str] = None
    amended_recommendations: Optional[str] = None


class RadiologyReportResponse(BaseModel):
    """Response schema for a Radiology Report."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: str
    study_id: int
    study_identifier: Optional[str] = None
    study_description: Optional[str] = None
    modality: Optional[str] = None
    body_site: Optional[str] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    order_id: Optional[int] = None
    status: str
    clinical_indication: str
    technique: str
    comparison_studies: str
    findings: str
    impression: str
    recommendations: str
    critical_findings_summary: Optional[str] = None
    is_critical: bool
    ai_assistance_metadata_json: Optional[dict[str, Any]] = None
    author_user_id: Optional[int] = None
    author_name: Optional[str] = None
    signed_by_user_id: Optional[int] = None
    signed_by_name: Optional[str] = None
    signed_at: Optional[datetime] = None
    amendment_reason: Optional[str] = None
    amended_from_report_id: Optional[int] = None
    provenance_hash: str
    created_at: datetime
    updated_at: datetime


class RadiologyReportListResponse(BaseModel):
    """List response for radiology reports."""

    items: list[RadiologyReportResponse]
    total: int


# =============================================================================
# Multimodal Analysis & Timeline Schemas
# =============================================================================

class MultimodalContextSnapshot(BaseModel):
    """Structured clinical context aggregated for multimodal AI interpretation."""

    patient_id: str
    patient_name: str
    age_years: int
    gender: str
    clinical_indication: str
    modality: str
    body_site: str
    active_diagnoses: list[str] = []
    active_medications: list[str] = []
    allergies: list[str] = []
    recent_vitals: list[dict[str, Any]] = []
    active_alerts: list[dict[str, Any]] = []
    relevant_lab_results: list[dict[str, Any]] = []
    previous_studies: list[dict[str, Any]] = []


class ImagingAnalysisResponse(BaseModel):
    """Response returned when executing AI interpretation on an imaging study."""

    study_id: str
    status: str
    findings_count: int
    critical_findings_count: int
    findings: list[ImagingFindingResponse]
    draft_report: Optional[RadiologyReportResponse] = None
    multimodal_context: MultimodalContextSnapshot
    provenance_hash: str
    evaluated_at: datetime


class ImagingTimelineItem(BaseModel):
    """Individual item in the longitudinal imaging timeline."""

    event_id: str
    study_id: str
    study_datetime: datetime
    modality: str
    body_site: str
    description: str
    status: str
    accession_number: str
    findings_count: int
    has_critical: bool
    report_id: Optional[str] = None
    report_status: Optional[str] = None


class ImagingTimelineResponse(BaseModel):
    """Longitudinal timeline response for a patient."""

    patient_id: str
    total_studies: int
    items: list[ImagingTimelineItem]

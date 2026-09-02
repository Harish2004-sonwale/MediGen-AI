"""Pydantic v2 schemas for Phase 9.0.29: DICOM PACS Medical Imaging & Multi-Lead ICU Waveforms."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.pacs_waveforms import (
    AlertLifecycleStatus,
    ArrhythmiaAlertSeverity,
    ArrhythmiaEventType,
    ClinicianReviewStatus,
    DICOMModality,
)


# ==============================================================================
# DICOM PACS Schemas (QIDO-RS / WADO-RS)
# ==============================================================================

class AILesionFindingCreate(BaseModel):
    lesion_type: str = Field(..., min_length=2, max_length=64)
    anatomical_location: str = Field(..., min_length=2, max_length=128)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    severity: str = "MODERATE"
    geometry_type: str = "BOUNDING_BOX"
    coordinates_json: Dict[str, Any]
    heatmap_matrix_json: Optional[Dict[str, Any]] = None
    model_name: str = "MediGen-VisionTransformer-v2.1"
    model_version: str = "2.1.0"


class AILesionFindingResponse(BaseModel):
    id: int
    finding_id: str
    instance_id: int
    lesion_type: str
    anatomical_location: str
    confidence_score: float
    severity: str
    geometry_type: str
    coordinates_json: Dict[str, Any]
    heatmap_matrix_json: Optional[Dict[str, Any]] = None
    model_name: str
    model_version: str
    clinician_review_status: ClinicianReviewStatus
    reviewed_by_user_id: Optional[int] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicianReviewFindingRequest(BaseModel):
    status: ClinicianReviewStatus
    review_notes: Optional[str] = None


class DICOMInstanceResponse(BaseModel):
    id: int
    sop_instance_uid: str
    series_id: int
    sop_class_uid: str
    instance_number: int
    rows: int
    columns: int
    bits_allocated: int
    bits_stored: int
    high_bit: int
    pixel_representation: int
    photometric_interpretation: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    pixel_data_preview_url: Optional[str] = None
    ai_findings: List[AILesionFindingResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DICOMSeriesResponse(BaseModel):
    id: int
    series_instance_uid: str
    study_id: int
    series_number: int
    series_description: str
    modality: DICOMModality
    body_part_examined: str
    patient_position: str
    slice_thickness_mm: Optional[float] = None
    pixel_spacing_row_mm: Optional[float] = None
    pixel_spacing_col_mm: Optional[float] = None
    window_center_default: float
    window_width_default: float
    rescale_intercept: float
    rescale_slope: float
    number_of_instances: int
    instances: List[DICOMInstanceResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DICOMStudyCreate(BaseModel):
    patient_id: str
    facility_id: Optional[str] = None
    accession_number: Optional[str] = None
    study_description: str = Field(..., min_length=3, max_length=255)
    modality: DICOMModality = DICOMModality.CT
    body_site: str = "CHEST"
    study_datetime: Optional[datetime] = None
    referring_physician: Optional[str] = None
    performing_institution: Optional[str] = None
    series_description: Optional[str] = None


class DICOMStudyResponse(BaseModel):
    id: int
    study_instance_uid: str
    study_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    facility_id: str
    accession_number: str
    study_description: str
    modality: DICOMModality
    body_site: str
    study_datetime: datetime
    referring_physician: Optional[str] = None
    performing_institution: str
    number_of_series: int
    number_of_instances: int
    dicom_attributes_json: Optional[Dict[str, Any]] = None
    series_list: List[DICOMSeriesResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DICOMStudyListResponse(BaseModel):
    total: int
    studies: List[DICOMStudyResponse]


# ==============================================================================
# Multi-Lead ICU Physiological Waveform Schemas
# ==============================================================================

class ECGSessionCreate(BaseModel):
    patient_id: str
    facility_id: Optional[str] = None
    encounter_id: Optional[int] = None
    device_id: str = "ICU-MONITOR-BED-04"
    lead_configuration: str = "12_LEAD"
    sample_rate_hz: int = 250
    duration_seconds: int = 60
    rhythm_state: ArrhythmiaEventType = ArrhythmiaEventType.NORMAL_SINUS_RHYTHM
    heart_rate_bpm: int = 75


class ArrhythmiaAlertResponse(BaseModel):
    id: int
    alert_id: str
    session_id: int
    patient_id: int
    event_type: ArrhythmiaEventType
    severity: ArrhythmiaAlertSeverity
    lead_involved: str
    heart_rate_bpm: int
    st_elevation_mm: Optional[float] = None
    alert_description: str
    status: AlertLifecycleStatus
    triggered_at: datetime
    cooldown_until: datetime
    acknowledged_by_user_id: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    clinician_action_taken: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ECGSessionResponse(BaseModel):
    id: int
    session_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    facility_id: str
    encounter_id: Optional[int] = None
    device_id: str
    lead_configuration: str
    sample_rate_hz: int
    amplitude_unit: str
    start_time: datetime
    duration_seconds: int
    current_rhythm_state: ArrhythmiaEventType
    heart_rate_bpm: int
    multi_lead_samples_json: Dict[str, Any]
    is_active_streaming: bool
    alerts: List[ArrhythmiaAlertResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ECGSessionListResponse(BaseModel):
    total: int
    sessions: List[ECGSessionResponse]


class AcknowledgeAlertRequest(BaseModel):
    clinician_action_taken: str = Field(..., min_length=3)
    status: AlertLifecycleStatus = AlertLifecycleStatus.ACKNOWLEDGED

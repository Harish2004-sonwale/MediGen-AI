"""SQLAlchemy models for Phase 9.0.29: DICOM PACS Medical Imaging & Real-Time Multi-Lead ICU Waveforms.

Standards Supported: DICOM QIDO-RS, WADO-RS, SOP Instance UIDs, Multi-Lead ECG, Debounced Arrhythmia Detection.
"""

from datetime import datetime
import enum
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class DICOMModality(str, enum.Enum):
    CT = "CT"
    MR = "MR"
    CR = "CR"
    DX = "DX"
    US = "US"
    XA = "XA"
    NM = "NM"
    PT = "PT"
    ECG = "ECG"
    OT = "OTHER"


class ArrhythmiaEventType(str, enum.Enum):
    STEMI_ELEVATION = "stemi_elevation"
    ATRIAL_FIBRILLATION = "atrial_fibrillation"
    VENTRICULAR_TACHYCARDIA = "ventricular_tachycardia"
    ASYSTOLE = "asystole"
    SEVERE_BRADYCARDIA = "severe_bradycardia"
    PREMATURE_VENTRICULAR_CONTRACTIONS = "pvc_bigeminy"
    NORMAL_SINUS_RHYTHM = "normal_sinus_rhythm"


class ArrhythmiaAlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    ADVISORY = "advisory"


class AlertLifecycleStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class ClinicianReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    AMENDED = "amended"


class DICOMStudyRecord(Base):
    """DICOM Study-level record conforming to DICOM PS3.3 / PS3.18 (QIDO-RS)."""

    __tablename__ = "dicom_study_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    study_instance_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    study_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    facility_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("clinical_facilities.facility_id", ondelete="RESTRICT"), index=True, nullable=False, default="FAC-METRO-MAIN"
    )
    accession_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    study_description: Mapped[str] = mapped_column(String(255), nullable=False)
    modality: Mapped[DICOMModality] = mapped_column(Enum(DICOMModality), nullable=False, index=True)
    body_site: Mapped[str] = mapped_column(String(64), nullable=False, default="CHEST")
    study_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    referring_physician: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    performing_institution: Mapped[str] = mapped_column(String(150), nullable=False, default="MetroHealth Diagnostic Imaging Center")
    number_of_series: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    number_of_instances: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    dicom_attributes_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    series_list: Mapped[list["DICOMSeriesRecord"]] = relationship(
        "DICOMSeriesRecord", back_populates="study", cascade="all, delete-orphan"
    )


class DICOMSeriesRecord(Base):
    """DICOM Series-level record containing geometric and acquisition parameters."""

    __tablename__ = "dicom_series_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    series_instance_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    study_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dicom_study_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    series_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    series_description: Mapped[str] = mapped_column(String(255), nullable=False)
    modality: Mapped[DICOMModality] = mapped_column(Enum(DICOMModality), nullable=False)
    body_part_examined: Mapped[str] = mapped_column(String(64), nullable=False, default="CHEST")
    patient_position: Mapped[str] = mapped_column(String(32), nullable=False, default="HFS")
    slice_thickness_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pixel_spacing_row_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.7)
    pixel_spacing_col_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.7)
    window_center_default: Mapped[float] = mapped_column(Float, default=40.0, nullable=False)
    window_width_default: Mapped[float] = mapped_column(Float, default=400.0, nullable=False)
    rescale_intercept: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rescale_slope: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    number_of_instances: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    study: Mapped["DICOMStudyRecord"] = relationship("DICOMStudyRecord", back_populates="series_list")
    instances: Mapped[list["DICOMInstanceRecord"]] = relationship(
        "DICOMInstanceRecord", back_populates="series", cascade="all, delete-orphan"
    )


class DICOMInstanceRecord(Base):
    """DICOM SOP Instance (individual 2D slice or image frame) supporting WADO-RS."""

    __tablename__ = "dicom_instance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    sop_instance_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dicom_series_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sop_class_uid: Mapped[str] = mapped_column(
        String(128), nullable=False, default="1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage SOP Class
    )
    instance_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    rows: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    columns: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    bits_allocated: Mapped[int] = mapped_column(Integer, default=16, nullable=False)
    bits_stored: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    high_bit: Mapped[int] = mapped_column(Integer, default=11, nullable=False)
    pixel_representation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    photometric_interpretation: Mapped[str] = mapped_column(String(32), default="MONOCHROME2", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pixel_data_preview_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    series: Mapped["DICOMSeriesRecord"] = relationship("DICOMSeriesRecord", back_populates="instances")
    ai_findings: Mapped[list["AIIsolatedLesionFinding"]] = relationship(
        "AIIsolatedLesionFinding", back_populates="instance", cascade="all, delete-orphan"
    )


class AIIsolatedLesionFinding(Base):
    """AI Medical Vision Finding with geometric coordinates, heatmap matrix & clinician review state."""

    __tablename__ = "ai_isolated_lesion_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    finding_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dicom_instance_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lesion_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    anatomical_location: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MODERATE")
    geometry_type: Mapped[str] = mapped_column(String(32), default="BOUNDING_BOX", nullable=False)
    coordinates_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # {"x": 140, "y": 210, "w": 65, "h": 70}
    heatmap_matrix_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Low-res attention weights
    model_name: Mapped[str] = mapped_column(String(100), default="MediGen-VisionTransformer-v2.1", nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="2.1.0", nullable=False)
    clinician_review_status: Mapped[ClinicianReviewStatus] = mapped_column(
        Enum(ClinicianReviewStatus), default=ClinicianReviewStatus.PENDING_REVIEW, nullable=False, index=True
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    instance: Mapped["DICOMInstanceRecord"] = relationship("DICOMInstanceRecord", back_populates="ai_findings")
    reviewed_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_user_id])


class ECGWaveformSession(Base):
    """High-frequency multi-lead ICU physiological waveform session."""

    __tablename__ = "ecg_waveform_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    facility_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("clinical_facilities.facility_id", ondelete="RESTRICT"), index=True, nullable=False, default="FAC-METRO-MAIN"
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
    )
    device_id: Mapped[str] = mapped_column(String(64), default="ICU-MONITOR-BED-04", nullable=False)
    lead_configuration: Mapped[str] = mapped_column(String(32), default="12_LEAD", nullable=False)  # 12_LEAD, 5_LEAD, 3_LEAD
    sample_rate_hz: Mapped[int] = mapped_column(Integer, default=250, nullable=False)
    amplitude_unit: Mapped[str] = mapped_column(String(16), default="mV", nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    current_rhythm_state: Mapped[ArrhythmiaEventType] = mapped_column(
        Enum(ArrhythmiaEventType), default=ArrhythmiaEventType.NORMAL_SINUS_RHYTHM, nullable=False
    )
    heart_rate_bpm: Mapped[int] = mapped_column(Integer, default=75, nullable=False)
    multi_lead_samples_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # {"I": [...], "II": [...], "V1": [...], ...}
    is_active_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    alerts: Mapped[list["ArrhythmiaAlertEvent"]] = relationship(
        "ArrhythmiaAlertEvent", back_populates="waveform_session", cascade="all, delete-orphan"
    )


class ArrhythmiaAlertEvent(Base):
    """Debounced clinical rhythm alert event with clinician review & cooldown tracking."""

    __tablename__ = "arrhythmia_alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ecg_waveform_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    event_type: Mapped[ArrhythmiaEventType] = mapped_column(
        Enum(ArrhythmiaEventType), nullable=False, index=True
    )
    severity: Mapped[ArrhythmiaAlertSeverity] = mapped_column(
        Enum(ArrhythmiaAlertSeverity), nullable=False, index=True
    )
    lead_involved: Mapped[str] = mapped_column(String(32), default="II", nullable=False)
    heart_rate_bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    st_elevation_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alert_description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AlertLifecycleStatus] = mapped_column(
        Enum(AlertLifecycleStatus), default=AlertLifecycleStatus.ACTIVE, nullable=False, index=True
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clinician_action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    waveform_session: Mapped["ECGWaveformSession"] = relationship("ECGWaveformSession", back_populates="alerts")
    patient: Mapped["Patient"] = relationship("Patient")
    acknowledged_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by_user_id])

"""SQLAlchemy models for Medical Imaging, Multimodal Diagnostics & Radiology Workflow.

Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ImagingStudy(Base):
    """Represents a structured clinical imaging study (X-Ray, CT, MRI, Ultrasound, etc.)."""

    __tablename__ = "imaging_studies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    study_id = Column(String(64), unique=True, index=True, nullable=False)  # STU-YYYYMMDD-HEX
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("clinical_orders.id", ondelete="SET NULL"), nullable=True, index=True)

    modality = Column(String(32), nullable=False, index=True)  # XRAY, CT, MRI, ULTRASOUND, MAMMOGRAPHY, PET_CT, ECHOCARDIOGRAPHY, OTHER
    body_site = Column(String(32), nullable=False, index=True)  # CHEST, ABDOMEN, PELVIS, HEAD_BRAIN, SPINE, EXTREMITY, CARDIAC, BREAST, NECK, OTHER
    study_description = Column(String(255), nullable=False)
    accession_number = Column(String(64), unique=True, index=True, nullable=False)  # ACC-YYYYMMDD-HEX
    study_datetime = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    performing_department = Column(String(100), nullable=False, default="Radiology & Diagnostic Imaging")
    referring_provider = Column(String(150), nullable=True)
    status = Column(String(32), nullable=False, default="ORDERED", index=True)  # ORDERED, SCHEDULED, IN_PROGRESS, COMPLETED, PRELIMINARY, FINAL, CANCELLED
    source = Column(String(50), nullable=False, default="PACS_IMPORT")  # PACS_IMPORT, DICOM_FEED, DIRECT_UPLOAD, EMR_SYNC
    external_identifier = Column(String(100), nullable=True)

    metadata_json = Column(JSON, nullable=True)  # DICOM series metadata, slice thickness, manufacturer, equipment info
    provenance_hash = Column(String(64), nullable=False)  # SHA-256 hash over payload

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    patient = relationship("Patient", backref="imaging_studies")
    encounter = relationship("Encounter", backref="imaging_studies")
    order = relationship("ClinicalOrder", backref="imaging_studies")
    assets = relationship("ImagingAsset", back_populates="study", cascade="all, delete-orphan")
    findings = relationship("ImagingFinding", back_populates="study", cascade="all, delete-orphan")
    reports = relationship("RadiologyReport", back_populates="study", cascade="all, delete-orphan")


class ImagingAsset(Base):
    """Represents a specific image or series asset within an Imaging Study."""

    __tablename__ = "imaging_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(64), unique=True, index=True, nullable=False)  # AST-YYYYMMDD-HEX
    study_id = Column(Integer, ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False, index=True)

    series_instance_uid = Column(String(128), nullable=True, index=True)
    sop_instance_uid = Column(String(128), nullable=True, index=True)
    series_number = Column(Integer, nullable=True, default=1)
    instance_number = Column(Integer, nullable=True, default=1)
    series_description = Column(String(255), nullable=True)

    modality = Column(String(32), nullable=False)
    body_site = Column(String(32), nullable=True)
    mime_type = Column(String(100), nullable=False, default="image/png")
    file_size_bytes = Column(Integer, nullable=False, default=0)
    storage_path = Column(String(500), nullable=False)
    thumbnail_storage_path = Column(String(500), nullable=True)

    image_dimensions = Column(JSON, nullable=True)  # {"width": 1024, "height": 1024, "slices": 1}
    dicom_metadata_json = Column(JSON, nullable=True)  # KV pairs, window center/width, orientation
    provenance_hash = Column(String(64), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    study = relationship("ImagingStudy", back_populates="assets")
    findings = relationship("ImagingFinding", back_populates="asset")


class ImagingFinding(Base):
    """Represents a structured finding (observed, AI-assisted, or clinician-confirmed)."""

    __tablename__ = "imaging_findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    finding_id = Column(String(64), unique=True, index=True, nullable=False)  # FND-YYYYMMDD-HEX
    study_id = Column(Integer, ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("imaging_assets.id", ondelete="SET NULL"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)

    finding_type = Column(String(64), nullable=False, index=True)  # NORMAL_APPEARANCE, POSSIBLE_NODULE, POSSIBLE_FRACTURE, POSSIBLE_PNEUMONIA, POSSIBLE_EFFUSION, POSSIBLE_HEMORRHAGE, POSSIBLE_MASS, OTHER_ABNORMALITY
    anatomical_location = Column(String(128), nullable=False)
    laterality = Column(String(32), nullable=False, default="NOT_APPLICABLE")  # LEFT, RIGHT, BILATERAL, MIDLINE, NOT_APPLICABLE
    severity = Column(String(32), nullable=False, default="NORMAL", index=True)  # NORMAL, MILD, MODERATE, SEVERE, CRITICAL
    confidence_score = Column(Float, nullable=False, default=1.0)
    is_critical = Column(Boolean, nullable=False, default=False, index=True)
    finding_nature = Column(String(32), nullable=False, default="AI_GENERATED_FINDING")  # OBSERVED_FACT, AI_GENERATED_FINDING, CLINICIAN_CONFIRMED_FINDING

    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    bounding_box_json = Column(JSON, nullable=True)  # {"x": 120, "y": 240, "width": 80, "height": 80}

    clinician_review_status = Column(String(32), nullable=False, default="pending_review", index=True)  # pending_review, confirmed, rejected, amended
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    provenance_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    study = relationship("ImagingStudy", back_populates="findings")
    asset = relationship("ImagingAsset", back_populates="findings")
    patient = relationship("Patient")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])


class RadiologyReport(Base):
    """Represents a structured Radiology Diagnostic Report with formal clinician review lifecycle."""

    __tablename__ = "radiology_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)  # RAD-YYYYMMDD-HEX
    study_id = Column(Integer, ForeignKey("imaging_studies.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("clinical_orders.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(32), nullable=False, default="DRAFT", index=True)  # DRAFT, AI_ASSISTED, RADIOLOGIST_REVIEW, FINALIZED, AMENDED
    clinical_indication = Column(Text, nullable=False)
    technique = Column(Text, nullable=False)
    comparison_studies = Column(Text, nullable=False, default="None available.")
    findings = Column(Text, nullable=False)
    impression = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=False)
    critical_findings_summary = Column(Text, nullable=True)
    is_critical = Column(Boolean, nullable=False, default=False, index=True)

    ai_assistance_metadata_json = Column(JSON, nullable=True)  # Model name, version, inference duration, multimodal context snapshot
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)

    amendment_reason = Column(Text, nullable=True)
    amended_from_report_id = Column(Integer, ForeignKey("radiology_reports.id", ondelete="SET NULL"), nullable=True)

    provenance_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    study = relationship("ImagingStudy", back_populates="reports")
    patient = relationship("Patient")
    encounter = relationship("Encounter")
    order = relationship("ClinicalOrder")
    author_user = relationship("User", foreign_keys=[author_user_id])
    signed_by_user = relationship("User", foreign_keys=[signed_by_user_id])
    amended_from_report = relationship("RadiologyReport", remote_side=[id])

"""SQLAlchemy ORM models for Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting.

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
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


class QualityMeasure(Base):
    """Represents a standardized clinical quality measure definition (e.g. HEDIS/MIPS/CQM)."""

    __tablename__ = "quality_measures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    measure_id = Column(String(64), unique=True, index=True, nullable=False)  # e.g. CQM-001-DM-HBA1C
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String(20), nullable=False, default="1.0.0")
    domain = Column(String(50), nullable=False, default="chronic_disease_management", index=True)
    hedis_mips_reference = Column(String(100), nullable=True)

    denominator_criteria_json = Column(JSON, nullable=True)
    numerator_criteria_json = Column(JSON, nullable=True)
    exclusion_criteria_json = Column(JSON, nullable=True)

    target_compliance_rate = Column(Float, nullable=False, default=80.0)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    results = relationship("QualityMeasureResult", back_populates="measure", cascade="all, delete-orphan")
    gaps = relationship("QualityMeasureGap", back_populates="measure", cascade="all, delete-orphan")


class QualityMeasureResult(Base):
    """Represents a calculated patient-level evaluation for a specific quality measure."""

    __tablename__ = "quality_measure_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    result_id = Column(String(32), unique=True, index=True, nullable=False)  # QMR-YYYYMMDD-HEX
    measure_id = Column(Integer, ForeignKey("quality_measures.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)

    measurement_period_start = Column(DateTime(timezone=True), nullable=True)
    measurement_period_end = Column(DateTime(timezone=True), nullable=True)

    is_eligible = Column(Boolean, default=True, nullable=False)
    is_excluded = Column(Boolean, default=False, nullable=False)
    exclusion_reason = Column(Text, nullable=True)

    is_numerator_compliant = Column(Boolean, default=False, nullable=False)
    compliance_status = Column(String(30), nullable=False, default="non_compliant", index=True)  # compliant, non_compliant, excluded, missing_data

    evidence_json = Column(JSON, nullable=True)
    gap_reason = Column(Text, nullable=True)
    remediation_action = Column(Text, nullable=True)

    calculated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    measure = relationship("QualityMeasure", back_populates="results")
    patient = relationship("Patient", backref="quality_measure_results")
    calculated_by_user = relationship("User", foreign_keys=[calculated_by_user_id])
    gaps = relationship("QualityMeasureGap", back_populates="result", cascade="all, delete-orphan")


class QualityMeasureGap(Base):
    """Represents an active or resolved clinical care gap for a patient failing a quality measure."""

    __tablename__ = "quality_measure_gaps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    gap_id = Column(String(32), unique=True, index=True, nullable=False)  # QMG-YYYYMMDD-HEX
    result_id = Column(Integer, ForeignKey("quality_measure_results.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    measure_id = Column(Integer, ForeignKey("quality_measures.id", ondelete="CASCADE"), nullable=False, index=True)

    gap_type = Column(String(50), nullable=False, default="clinical_measure_gap")
    severity = Column(String(20), nullable=False, default="MODERATE", index=True)  # LOW, MODERATE, HIGH, CRITICAL
    status = Column(String(30), nullable=False, default="open", index=True)  # open, in_remediation, resolved, dismissed

    gap_description = Column(Text, nullable=False)
    missing_data_elements = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)

    linked_care_task_id = Column(Integer, ForeignKey("care_tasks.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    result = relationship("QualityMeasureResult", back_populates="gaps")
    patient = relationship("Patient", backref="quality_measure_gaps")
    measure = relationship("QualityMeasure", back_populates="gaps")
    linked_care_task = relationship("CareTask", foreign_keys=[linked_care_task_id])


class QualityMeasureReport(Base):
    """Represents an immutable, auditable population compliance report with provenance."""

    __tablename__ = "quality_measure_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(String(32), unique=True, index=True, nullable=False)  # QRP-YYYYMMDD-HEX
    title = Column(String(255), nullable=False)

    reporting_period_start = Column(DateTime(timezone=True), nullable=False)
    reporting_period_end = Column(DateTime(timezone=True), nullable=False)
    report_scope = Column(String(30), nullable=False, default="organization", index=True)  # organization, provider, cohort, measure

    total_eligible_population = Column(Integer, nullable=False, default=0)
    total_numerator_compliant = Column(Integer, nullable=False, default=0)
    overall_performance_rate = Column(Float, nullable=False, default=0.0)

    measure_summaries_json = Column(JSON, nullable=False)  # list of measure breakdown summaries
    audit_metadata_json = Column(JSON, nullable=True)  # audit provenance, calculation timestamp, hash, user ID

    generated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    generated_by_user = relationship("User", foreign_keys=[generated_by_user_id])

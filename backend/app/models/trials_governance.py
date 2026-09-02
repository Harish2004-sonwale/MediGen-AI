"""SQLAlchemy models for Multi-Center Clinical Trial Governance, Protocol Deviations & Regulatory Auditing.

Phase 9.0.27: Enterprise Clinical Trial Auto-Enrollment, Protocol Deviations, CAPA Tracking & Multi-Center Regulatory Auditing.
"""

from datetime import datetime, date
import enum
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    Date,
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
    from app.models.trials import ClinicalTrial


class StudySiteStatus(str, enum.Enum):
    ACTIVE = "active"
    RECRUITING_CLOSED = "recruiting_closed"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class DeviationSeverity(str, enum.Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class DeviationCategory(str, enum.Enum):
    INCLUSION_EXCLUSION_BREACH = "inclusion_exclusion_breach"
    INFORMED_CONSENT_VARIANCE = "informed_consent_variance"
    MISSED_STUDY_VISIT = "missed_study_visit"
    PROHIBITED_MEDICATION = "prohibited_medication"
    INVESTIGATIONAL_PRODUCT_DOSING_ERROR = "investigational_product_dosing_error"
    LABORATORY_OUT_OF_WINDOW = "laboratory_out_of_window"
    SAFETY_REPORTING_DELAY = "safety_reporting_delay"


class DeviationStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    CAPA_ASSIGNED = "capa_assigned"
    RESOLVED = "resolved"
    IRB_NOTIFIED = "irb_notified"


class CAPARootCause(str, enum.Enum):
    INVESTIGATOR_OVERSIGHT = "investigator_oversight"
    PATIENT_NONCOMPLIANCE = "patient_noncompliance"
    PHARMACY_DISPENSATION_DELAY = "pharmacy_dispensation_delay"
    LABORATORY_LOGISTICS_ERROR = "laboratory_logistics_error"
    STAFF_TRAINING_GAP = "staff_training_gap"
    PROTOCOL_AMBIGUITY = "protocol_ambiguity"


class CAPAStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    VERIFICATION_PENDING = "verification_pending"
    CLOSED = "closed"


class IRBSubmissionType(str, enum.Enum):
    INITIAL_DEVIATION_REPORT = "initial_deviation_report"
    FOLLOW_UP_CAPA = "follow_up_capa"
    PROMPT_SAFETY_REPORT_IND = "prompt_safety_report_ind"
    ANNUAL_CONTINUING_REVIEW = "annual_continuing_review"


class MultiCenterStudySite(Base):
    """Represents an active clinical research site participating in a multi-center trial."""

    __tablename__ = "multi_center_study_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trial_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clinical_trials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    facility_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("clinical_facilities.facility_id", ondelete="SET NULL"), index=True, nullable=True
    )
    principal_investigator_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_accrual: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    current_enrolled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    site_status: Mapped[StudySiteStatus] = mapped_column(
        Enum(StudySiteStatus), default=StudySiteStatus.ACTIVE, nullable=False, index=True
    )
    irb_approval_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    irb_approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    irb_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    trial: Mapped["ClinicalTrial"] = relationship("ClinicalTrial")
    deviations: Mapped[list["TrialProtocolDeviation"]] = relationship(
        "TrialProtocolDeviation", back_populates="site", cascade="all, delete-orphan"
    )


class TrialProtocolDeviation(Base):
    """Tracks protocol non-compliance, GCP deviations, and regulatory reporting triggers."""

    __tablename__ = "trial_protocol_deviations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    deviation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trial_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clinical_trials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    site_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("multi_center_study_sites.id", ondelete="SET NULL"), index=True, nullable=True
    )
    patient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"), index=True, nullable=True
    )
    reported_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    deviation_category: Mapped[DeviationCategory] = mapped_column(
        Enum(DeviationCategory), nullable=False, index=True
    )
    severity: Mapped[DeviationSeverity] = mapped_column(
        Enum(DeviationSeverity), default=DeviationSeverity.MINOR, nullable=False, index=True
    )
    status: Mapped[DeviationStatus] = mapped_column(
        Enum(DeviationStatus), default=DeviationStatus.OPEN, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impact_on_patient_safety: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_on_data_integrity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_irb_submission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    irb_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    trial: Mapped["ClinicalTrial"] = relationship("ClinicalTrial")
    site: Mapped[Optional["MultiCenterStudySite"]] = relationship("MultiCenterStudySite", back_populates="deviations")
    patient: Mapped[Optional["Patient"]] = relationship("Patient")
    reporter: Mapped["User"] = relationship("User")
    capas: Mapped[list["TrialCAPARecord"]] = relationship(
        "TrialCAPARecord", back_populates="deviation", cascade="all, delete-orphan"
    )
    irb_notifications: Mapped[list["TrialIRBNotification"]] = relationship(
        "TrialIRBNotification", back_populates="deviation", cascade="all, delete-orphan"
    )


class TrialCAPARecord(Base):
    """Corrective and Preventive Action (CAPA) tracking record for protocol deviations."""

    __tablename__ = "trial_capa_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    capa_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    deviation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trial_protocol_deviations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    root_cause_category: Mapped[CAPARootCause] = mapped_column(
        Enum(CAPARootCause), default=CAPARootCause.INVESTIGATOR_OVERSIGHT, nullable=False
    )
    root_cause_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    corrective_action: Mapped[str] = mapped_column(Text, nullable=False)
    preventive_action: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    target_resolution_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_resolution_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[CAPAStatus] = mapped_column(
        Enum(CAPAStatus), default=CAPAStatus.IN_PROGRESS, nullable=False, index=True
    )
    effectiveness_check_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    deviation: Mapped["TrialProtocolDeviation"] = relationship("TrialProtocolDeviation", back_populates="capas")
    owner: Mapped["User"] = relationship("User")


class TrialIRBNotification(Base):
    """Immutable audit record of regulatory communications and IRB safety filings."""

    __tablename__ = "trial_irb_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    notification_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    deviation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trial_protocol_deviations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    irb_committee_name: Mapped[str] = mapped_column(String(150), nullable=False)
    submission_type: Mapped[IRBSubmissionType] = mapped_column(
        Enum(IRBSubmissionType), nullable=False, index=True
    )
    document_content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submission_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledgement_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    deviation: Mapped["TrialProtocolDeviation"] = relationship(
        "TrialProtocolDeviation", back_populates="irb_notifications"
    )
    submitter: Mapped["User"] = relationship("User")

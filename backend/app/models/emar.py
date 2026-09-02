"""SQLAlchemy models for Closed-Loop Medication Administration Record (eMAR) & Barcode Medication Administration (BCMA).

Phase 9.0.28: Closed-Loop eMAR & Barcode Verification (BCMA), 5-Rights Safety Engine, Dual-Clinician High-Alert Signoff.
"""

from datetime import datetime
import enum
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
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
    from app.models.order import ClinicalOrder


class MARStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    GIVEN = "administered"
    HELD = "held"
    REFUSED = "refused"
    MISSED = "missed"
    DISCONTINUED = "discontinued"


class BCMAVerificationStatus(str, enum.Enum):
    PASS = "pass"
    WARNING_OVERRIDE = "warning_override"
    MISMATCH_REJECTED = "mismatch_rejected"


class HighAlertMedicationCategory(str, enum.Enum):
    INSULIN = "insulin"
    ANTICOAGULANT = "anticoagulant"
    OPIOID_NARCOTIC = "opioid_narcotic"
    CHEMOTHERAPY = "chemotherapy"
    NEUROMUSCULAR_BLOCKER = "neuromuscular_blocker"
    CONCENTRATED_ELECTROLYTE = "concentrated_electrolyte"
    GENERAL = "general"


class MedicationBarcodeDirectory(Base):
    """Barcode and GS1-128 / NDC directory for medication packaging verification."""

    __tablename__ = "medication_barcode_directory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    barcode: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rxnorm_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ndc_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    standard_dose: Mapped[str] = mapped_column(String(64), nullable=False)
    dosage_form: Mapped[str] = mapped_column(String(64), nullable=False, default="tablet")
    route: Mapped[str] = mapped_column(String(64), nullable=False, default="oral")
    is_high_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    high_alert_category: Mapped[Optional[HighAlertMedicationCategory]] = mapped_column(
        Enum(HighAlertMedicationCategory), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MedicationAdministrationRecord(Base):
    """Scheduled and administered doses in the closed-loop eMAR schedule."""

    __tablename__ = "medication_administration_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    mar_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clinical_orders.id", ondelete="SET NULL"), index=True, nullable=True
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    facility_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("clinical_facilities.facility_id", ondelete="RESTRICT"), index=True, nullable=False, default="FAC-METRO-MAIN"
    )
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    medication_code: Mapped[str] = mapped_column(String(64), nullable=False)
    prescribed_dose: Mapped[str] = mapped_column(String(64), nullable=False)
    prescribed_route: Mapped[str] = mapped_column(String(64), nullable=False)
    prescribed_frequency: Mapped[str] = mapped_column(String(64), nullable=False, default="daily")
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actual_admin_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MARStatus] = mapped_column(
        Enum(MARStatus), default=MARStatus.SCHEDULED, nullable=False, index=True
    )
    administering_nurse_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    administered_dose: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    administered_route: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    site_of_administration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_high_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    requires_dual_witness: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dual_witness_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dual_witness_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    variance_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    patient_response_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vital_signs_pre_admin_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    barcode_scanned_patient_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    barcode_scanned_med_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verification_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    order: Mapped[Optional["ClinicalOrder"]] = relationship("ClinicalOrder")
    administering_nurse: Mapped[Optional["User"]] = relationship("User", foreign_keys=[administering_nurse_id])
    dual_witness_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[dual_witness_user_id])


class BCMAVerificationLog(Base):
    """Immutable audit trail of barcode scanner verification events at the bedside."""

    __tablename__ = "bcma_verification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    mar_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("medication_administration_records.id", ondelete="SET NULL"), nullable=True
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    scanned_patient_barcode: Mapped[str] = mapped_column(String(128), nullable=False)
    scanned_med_barcode: Mapped[str] = mapped_column(String(128), nullable=False)
    patient_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    medication_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dose_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    route_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    time_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verification_status: Mapped[BCMAVerificationStatus] = mapped_column(
        Enum(BCMAVerificationStatus), nullable=False, index=True
    )
    mismatch_details_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    user: Mapped["User"] = relationship("User")
    mar_record: Mapped[Optional["MedicationAdministrationRecord"]] = relationship("MedicationAdministrationRecord")

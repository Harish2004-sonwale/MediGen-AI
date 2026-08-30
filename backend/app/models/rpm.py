"""SQLAlchemy models for Remote Patient Monitoring (RPM), PROMs & Telehealth.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
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
    from app.models.appointment import Appointment
    from app.models.care_task import CareTask
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User


class RPMProgram(Base):
    """Enrollment of patients into clinical remote monitoring protocols."""

    __tablename__ = "rpm_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    program_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    enrolled_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    condition_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True, nullable=False)
    target_cadence_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    clinical_goals_json: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    discharged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship("Patient", backref="rpm_programs")
    enrolled_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[enrolled_by_user_id])


class RPMDevice(Base):
    """Registered connected medical device or wearable for remote patient monitoring."""

    __tablename__ = "rpm_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="SET NULL"), index=True, nullable=True
    )
    device_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model_number: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True, nullable=False)
    supported_measurements_json: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )

    patient: Mapped[Optional["Patient"]] = relationship("Patient", backref="rpm_devices")


class RPMObservation(Base):
    """Ingested continuous physiological measurement or telemetry record."""

    __tablename__ = "rpm_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("rpm_devices.id", ondelete="SET NULL"), index=True, nullable=True
    )
    observation_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    numeric_value: Mapped[float] = mapped_column(Float, nullable=False)
    secondary_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False)
    classification: Mapped[str] = mapped_column(String(30), default="normal", index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="bluetooth_sync", nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_payload_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", backref="rpm_observations")
    device: Mapped[Optional["RPMDevice"]] = relationship("RPMDevice", backref="observations")


class RPMThresholdRule(Base):
    """Clinical threshold boundary configuration for remote patient monitoring."""

    __tablename__ = "rpm_threshold_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=True
    )
    observation_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    normal_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    normal_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    consecutive_readings_trigger: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )


class RPMEscalationAlert(Base):
    """Escalated critical or repeated abnormal telemetry incident."""

    __tablename__ = "rpm_escalation_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    observation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("rpm_observations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    severity: Mapped[str] = mapped_column(String(20), default="HIGH", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True, nullable=False)
    escalation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linked_care_task_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("care_tasks.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", backref="rpm_escalations")
    observation: Mapped[Optional["RPMObservation"]] = relationship("RPMObservation", backref="escalation_alerts")
    linked_care_task: Mapped[Optional["CareTask"]] = relationship("CareTask")


class PROMDefinition(Base):
    """Standardized Patient-Reported Outcome Measure (PROM) survey template."""

    __tablename__ = "prom_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    prom_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), default="symptom_burden", index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    questions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    scoring_method: Mapped[str] = mapped_column(String(50), default="sum_total", nullable=False)
    interpretation_ranges_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )


class PROMResponse(Base):
    """Patient submission for a PROM questionnaire with deterministic scoring."""

    __tablename__ = "prom_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    response_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    prom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prom_definitions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
    )
    answers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    calculated_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity_interpretation: Mapped[str] = mapped_column(String(100), nullable=False)
    clinical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    prom: Mapped["PROMDefinition"] = relationship("PROMDefinition", backref="responses")
    patient: Mapped["Patient"] = relationship("Patient", backref="prom_responses")


class TelehealthSession(Base):
    """Virtual telehealth consultation session with pre-visit clinical briefings."""

    __tablename__ = "telehealth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    clinician_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    appointment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True, nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    visit_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    pre_visit_rpm_summary_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    pre_visit_prom_summary_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    session_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    followup_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship("Patient", backref="telehealth_sessions")
    clinician: Mapped["User"] = relationship("User", foreign_keys=[clinician_user_id])
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment")
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")

from datetime import datetime
import hashlib
import json
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class AuditAction(str):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    EXPORT = "EXPORT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CONSENT_GRANT = "CONSENT_GRANT"
    CONSENT_REVOKE = "CONSENT_REVOKE"
    SECURITY_ALERT = "SECURITY_ALERT"
    HOLD_APPLIED = "HOLD_APPLIED"
    HOLD_RELEASED = "HOLD_RELEASED"


class AuditOutcome(str):
    SUCCESS = "SUCCESS"
    DENIED_FORBIDDEN = "DENIED_FORBIDDEN"
    DENIED_NO_CONSENT = "DENIED_NO_CONSENT"
    ERROR = "ERROR"
    WARNING = "WARNING"


class ConsentStatus(str):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class ConsentPolicyRule(str):
    PERMIT = "PERMIT"
    DENY = "DENY"


class ConsentScope(str):
    ALL_RECORDS = "ALL_RECORDS"
    GENOMICS_ONLY = "GENOMICS_ONLY"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    BEHAVIORAL_HEALTH = "BEHAVIORAL_HEALTH"
    IMAGING_ONLY = "IMAGING_ONLY"
    TREATMENT_CARE_TEAM = "TREATMENT_CARE_TEAM"
    RESTRICT_EXPORT = "RESTRICT_EXPORT"
    THIRD_PARTY_DISCLOSURE = "THIRD_PARTY_DISCLOSURE"


class IncidentSeverity(str):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class IncidentEventType(str):
    SUSPICIOUS_BULK_EXPORT = "SUSPICIOUS_BULK_EXPORT"
    CROSS_PATIENT_ACCESS_ATTEMPT = "CROSS_PATIENT_ACCESS_ATTEMPT"
    REPEATED_AUTH_FAILURE = "REPEATED_AUTH_FAILURE"
    CONSENT_VIOLATION_ATTEMPT = "CONSENT_VIOLATION_ATTEMPT"
    AUDIT_TAMPER_DETECTED = "AUDIT_TAMPER_DETECTED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED_ROLE_ESCALATION = "UNAUTHORIZED_ROLE_ESCALATION"


class HoldStatus(str):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class ClinicalAuditEvent(Base):
    """Immutable, tamper-evident clinical audit record with cryptographic hash-chaining."""

    __tablename__ = "clinical_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        index=True,
        nullable=False,
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_role: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="ANONYMOUS")
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(64), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purpose_of_use: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default="TREATMENT"
    )
    outcome: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=AuditOutcome.SUCCESS
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    prev_record_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default="0" * 64
    )
    record_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    @staticmethod
    def calculate_hash(
        prev_hash: str,
        event_id: str,
        timestamp_iso: str,
        user_id: Optional[int],
        patient_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        outcome: str,
    ) -> str:
        payload = f"{prev_hash}|{event_id}|{timestamp_iso}|{user_id or ''}|{patient_id or ''}|{action}|{resource_type}|{resource_id or ''}|{outcome}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<ClinicalAuditEvent id={self.id} event_id={self.event_id} action={self.action} resource={self.resource_type}>"


class PatientConsent(Base):
    """Patient consent directive governing use and disclosure of medical data."""

    __tablename__ = "patient_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    consent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("patients.patient_id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=ConsentStatus.ACTIVE
    )
    scope: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=ConsentScope.ALL_RECORDS
    )
    policy_rule: Mapped[str] = mapped_column(
        String(16), index=True, nullable=False, default=ConsentPolicyRule.PERMIT
    )
    purpose_of_use: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default="TREATMENT"
    )
    data_category: Mapped[Optional[str]] = mapped_column(
        String(64), index=True, nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CARE_TEAM"
    )
    actor_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signed_by_patient: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    signer_relationship: Mapped[str] = mapped_column(
        String(32), default="SELF", nullable=False
    )
    witness_or_clinician_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    revoked_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    digital_signature_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UNVERIFIED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", foreign_keys=[patient_id])
    witness: Mapped[Optional["User"]] = relationship("User", foreign_keys=[witness_or_clinician_id])
    revoked_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[revoked_by_user_id])

    @staticmethod
    def compute_signature_hash(
        patient_id: str,
        scope: str,
        policy_rule: str,
        purpose_of_use: str,
        signer_name: str,
        valid_from_iso: str,
    ) -> str:
        payload = f"CONSENT|{patient_id}|{scope}|{policy_rule}|{purpose_of_use}|{signer_name}|{valid_from_iso}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<PatientConsent id={self.id} consent_id={self.consent_id} patient={self.patient_id} status={self.status}>"


class SecurityIncident(Base):
    """Triaged security threat, unauthorized access attempt, or policy violation."""

    __tablename__ = "security_incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        index=True,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(16), index=True, nullable=False, default=IncidentSeverity.MEDIUM
    )
    status: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=IncidentStatus.OPEN
    )
    event_type: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(64), index=True, nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    resolved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_user_id])

    def __repr__(self) -> str:
        return f"<SecurityIncident id={self.id} incident_id={self.incident_id} severity={self.severity} status={self.status}>"


class DataRetentionPolicy(Base):
    """Regulatory data retention schedules and disposition rules."""

    __tablename__ = "data_retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    data_category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    retention_period_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2555  # Default 7 years (7 * 365)
    )
    action_on_expiry: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FLAG_REVIEW"
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DataRetentionPolicy id={self.id} code={self.policy_code} category={self.data_category}>"


class LegalClinicalHold(Base):
    """Legal and investigational hold that strictly prevents record deletion or archival."""

    __tablename__ = "legal_clinical_holds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    hold_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(64), index=True, nullable=True
    )
    scope_category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="ALL_RECORDS"
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False, default=HoldStatus.ACTIVE
    )
    placed_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    released_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    placed_by: Mapped["User"] = relationship("User", foreign_keys=[placed_by_user_id])
    released_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[released_by_user_id])

    def __repr__(self) -> str:
        return f"<LegalClinicalHold id={self.id} hold_id={self.hold_id} patient={self.patient_id} status={self.status}>"

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.security import (
    AuditAction,
    AuditOutcome,
    ConsentPolicyRule,
    ConsentScope,
    ConsentStatus,
    HoldStatus,
    IncidentEventType,
    IncidentSeverity,
    IncidentStatus,
)


# ============================================================================
# AUDIT SCHEMAS
# ============================================================================

class ClinicalAuditEventResponse(BaseModel):
    id: int
    event_id: str
    timestamp: datetime
    user_id: Optional[int] = None
    user_role: str
    patient_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    purpose_of_use: str
    outcome: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    prev_record_hash: str
    record_hash: str

    model_config = ConfigDict(from_attributes=True)


class AuditEventListResponse(BaseModel):
    events: list[ClinicalAuditEventResponse]
    total_count: int
    page: int
    page_size: int


class AuditIntegrityVerificationResponse(BaseModel):
    verified_at: datetime
    total_records_checked: int
    tamper_detected: bool
    broken_links_count: int
    tampered_event_ids: list[str] = Field(default_factory=list)
    chain_head_hash: Optional[str] = None
    status: str = Field(description="'VALID' or 'COMPROMISED'")


# ============================================================================
# PATIENT CONSENT SCHEMAS
# ============================================================================

class PatientConsentCreateRequest(BaseModel):
    scope: str = Field(default=ConsentScope.ALL_RECORDS, description="Consent scope")
    policy_rule: str = Field(default=ConsentPolicyRule.PERMIT, description="PERMIT or DENY")
    purpose_of_use: str = Field(default="TREATMENT", description="TREATMENT, RESEARCH, THIRD_PARTY_SHARING, etc.")
    data_category: Optional[str] = Field(default=None, description="GENOMICS, PSYCHIATRY, IMAGING, GENERAL_CLINICAL, etc.")
    actor_type: str = Field(default="CARE_TEAM", description="CARE_TEAM, ORGANIZATION, ALL_USERS, etc.")
    actor_reference: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    signed_by_patient: bool = True
    signer_name: str = Field(..., min_length=2, max_length=128)
    signer_relationship: str = Field(default="SELF")
    witness_or_clinician_id: Optional[int] = None


class PatientConsentRevokeRequest(BaseModel):
    revocation_reason: str = Field(..., min_length=3, max_length=255)


class PatientConsentResponse(BaseModel):
    id: int
    consent_id: str
    patient_id: str
    status: str
    scope: str
    policy_rule: str
    purpose_of_use: str
    data_category: Optional[str] = None
    actor_type: str
    actor_reference: Optional[str] = None
    valid_from: datetime
    valid_to: Optional[datetime] = None
    signed_by_patient: bool
    signer_name: str
    signer_relationship: str
    witness_or_clinician_id: Optional[int] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    revoked_by_user_id: Optional[int] = None
    digital_signature_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsentVerificationRequest(BaseModel):
    patient_id: str
    resource_type: str
    action: str = Field(default="READ")
    purpose_of_use: str = Field(default="TREATMENT")
    data_category: Optional[str] = None


class ConsentVerificationResponse(BaseModel):
    patient_id: str
    resource_type: str
    action: str
    purpose_of_use: str
    is_permitted: bool
    reason: str
    matched_consent_id: Optional[str] = None
    is_emergency_override: bool = False


# ============================================================================
# SECURITY INCIDENT SCHEMAS
# ============================================================================

class SecurityIncidentCreateRequest(BaseModel):
    severity: str = Field(default=IncidentSeverity.MEDIUM)
    event_type: str = Field(default=IncidentEventType.CROSS_PATIENT_ACCESS_ATTEMPT)
    user_id: Optional[int] = None
    patient_id: Optional[str] = None
    ip_address: Optional[str] = None
    description: str = Field(..., max_length=500)
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityIncidentUpdateRequest(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    resolution_notes: Optional[str] = None


class SecurityIncidentResponse(BaseModel):
    id: int
    incident_id: str
    detected_at: datetime
    severity: str
    status: str
    event_type: str
    user_id: Optional[int] = None
    patient_id: Optional[str] = None
    ip_address: Optional[str] = None
    description: str
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    assigned_to_user_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityScanResult(BaseModel):
    scanned_at: datetime
    events_analyzed: int
    anomalies_detected: int
    new_incidents_created: int
    incident_ids: list[str] = Field(default_factory=list)


# ============================================================================
# RETENTION & LEGAL HOLD SCHEMAS
# ============================================================================

class DataRetentionPolicyCreateRequest(BaseModel):
    policy_code: str = Field(..., min_length=3, max_length=32)
    data_category: str = Field(..., min_length=2, max_length=64)
    retention_period_days: int = Field(default=2555)
    action_on_expiry: str = Field(default="FLAG_REVIEW")
    description: str = Field(..., min_length=3, max_length=255)
    is_active: bool = True


class DataRetentionPolicyResponse(BaseModel):
    id: int
    policy_code: str
    data_category: str
    retention_period_days: int
    action_on_expiry: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LegalClinicalHoldCreateRequest(BaseModel):
    patient_id: Optional[str] = None
    scope_category: str = Field(default="ALL_RECORDS")
    reason: str = Field(..., min_length=3, max_length=255)
    notes: Optional[str] = None


class LegalClinicalHoldReleaseRequest(BaseModel):
    notes: Optional[str] = None


class LegalClinicalHoldResponse(BaseModel):
    id: int
    hold_id: str
    patient_id: Optional[str] = None
    scope_category: str
    reason: str
    status: str
    placed_by_user_id: int
    placed_at: datetime
    released_by_user_id: Optional[int] = None
    released_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# COMPLIANCE SUMMARY SCHEMA
# ============================================================================

class ComplianceSummaryResponse(BaseModel):
    generated_at: datetime
    total_audit_events: int
    recent_audit_events_24h: int
    audit_tamper_integrity_status: str
    total_active_consents: int
    total_revoked_consents: int
    open_security_incidents: int
    critical_security_incidents: int
    active_legal_holds: int
    active_retention_policies: int
    compliance_score_percent: float
    status: str

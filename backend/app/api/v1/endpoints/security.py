from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.security import (
    AuditEventListResponse,
    AuditIntegrityVerificationResponse,
    ClinicalAuditEventResponse,
    ComplianceSummaryResponse,
    ConsentVerificationRequest,
    ConsentVerificationResponse,
    DataRetentionPolicyCreateRequest,
    DataRetentionPolicyResponse,
    LegalClinicalHoldCreateRequest,
    LegalClinicalHoldReleaseRequest,
    LegalClinicalHoldResponse,
    PatientConsentCreateRequest,
    PatientConsentResponse,
    PatientConsentRevokeRequest,
    SecurityIncidentCreateRequest,
    SecurityIncidentResponse,
    SecurityIncidentUpdateRequest,
    SecurityScanResult,
)
from app.schemas.task import BackgroundTaskResponse
from app.services.audit_service import audit_service
from app.services.compliance_reporting_service import compliance_reporting_service
from app.services.consent_service import consent_service
from app.services.security_monitoring_service import security_monitoring_service
from app.services.task_service import (
    enqueue_audit_integrity_task,
    enqueue_compliance_report_task,
    enqueue_security_scan_task,
)

router = APIRouter(tags=["Clinical Security, Auditability, Consent & Compliance"])


# Helper to format background task responses
def _build_task_response(task) -> BackgroundTaskResponse:
    return BackgroundTaskResponse.model_validate(task)


# ============================================================================
# AUDIT TRAIL ENDPOINTS
# ============================================================================

@router.get(
    "/audit/events",
    response_model=AuditEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="Query and filter immutable clinical audit trail",
)
def get_audit_events(
    patient_id: Optional[str] = Query(None, description="Filter by patient public identifier"),
    user_id: Optional[int] = Query(None, description="Filter by user identifier"),
    action: Optional[str] = Query(None, description="Filter by audit action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    outcome: Optional[str] = Query(None, description="Filter by outcome status"),
    from_date: Optional[datetime] = Query(None, description="Filter from timestamp"),
    to_date: Optional[datetime] = Query(None, description="Filter to timestamp"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> AuditEventListResponse:
    """Retrieve filtered, paginated audit records."""
    return audit_service.query_audit_events(
        db=db,
        patient_id=patient_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        outcome=outcome,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/audit/events/{event_id}",
    response_model=ClinicalAuditEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single audit event with cryptographic hash",
)
def get_audit_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ClinicalAuditEventResponse:
    """Fetch specific audit event by ID."""
    event = audit_service.get_audit_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audit event '{event_id}' not found")
    return ClinicalAuditEventResponse.model_validate(event)


@router.post(
    "/audit/verify-integrity",
    response_model=AuditIntegrityVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic SHA-256 hash-chain integrity across audit trail",
)
def verify_audit_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> AuditIntegrityVerificationResponse:
    """Walk and verify complete audit trail hash chain."""
    return audit_service.verify_audit_trail_integrity(db)


# ============================================================================
# PATIENT CONSENT ENDPOINTS
# ============================================================================

@router.post(
    "/patients/{patient_id}/consents",
    response_model=PatientConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant and register a new patient consent directive",
)
def create_patient_consent(
    patient_id: str,
    request: PatientConsentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PatientConsentResponse:
    """Register a new consent directive with digital signature hashing."""
    try:
        consent = consent_service.grant_consent(
            db=db,
            patient_id_str=patient_id,
            request=request,
            current_user=current_user,
        )
        return PatientConsentResponse.model_validate(consent)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/consents",
    response_model=list[PatientConsentResponse],
    status_code=status.HTTP_200_OK,
    summary="List consent directives for a patient",
)
def get_patient_consents(
    patient_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[PatientConsentResponse]:
    """Retrieve chronological consent directives."""
    try:
        consents = consent_service.list_patient_consents(db, patient_id, status=status_filter)
        return [PatientConsentResponse.model_validate(c) for c in consents]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/consents/{consent_id}",
    response_model=PatientConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single consent directive details",
)
def get_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PatientConsentResponse:
    """Fetch consent directive by ID."""
    consent = consent_service.get_consent_by_id(db, consent_id)
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Consent directive '{consent_id}' not found")
    return PatientConsentResponse.model_validate(consent)


@router.post(
    "/consents/{consent_id}/revoke",
    response_model=PatientConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Immediately revoke an active consent directive",
)
def revoke_patient_consent(
    consent_id: str,
    request: PatientConsentRevokeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PatientConsentResponse:
    """Revoke consent directive with immediate effect."""
    try:
        revoked = consent_service.revoke_consent(
            db=db,
            consent_id=consent_id,
            request=request,
            current_user=current_user,
        )
        return PatientConsentResponse.model_validate(revoked)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/consents/verify",
    response_model=ConsentVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate active patient consent policies against clinical operation",
)
def verify_patient_consent(
    request: ConsentVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConsentVerificationResponse:
    """Verify if a clinical action or export is permitted by active consents."""
    try:
        return consent_service.verify_consent(
            db=db,
            request=request,
            current_user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ============================================================================
# SECURITY INCIDENTS & THREAT DETECTION
# ============================================================================

@router.get(
    "/security/incidents",
    response_model=list[SecurityIncidentResponse],
    status_code=status.HTTP_200_OK,
    summary="List triaged security incidents and threat detections",
)
def list_security_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[SecurityIncidentResponse]:
    """Retrieve security incidents."""
    incidents, _ = security_monitoring_service.list_incidents(
        db=db,
        status=status_filter,
        severity=severity,
        page=page,
        page_size=page_size,
    )
    return [SecurityIncidentResponse.model_validate(i) for i in incidents]


@router.get(
    "/security/incidents/{incident_id}",
    response_model=SecurityIncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single security incident details and evidence",
)
def get_security_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> SecurityIncidentResponse:
    """Fetch security incident by ID."""
    incident = security_monitoring_service.get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Security incident '{incident_id}' not found")
    return SecurityIncidentResponse.model_validate(incident)


@router.post(
    "/security/incidents",
    response_model=SecurityIncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new security incident manually or programmatically",
)
def create_security_incident(
    request: SecurityIncidentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> SecurityIncidentResponse:
    """Create a security incident."""
    incident = security_monitoring_service.create_incident(db, request, current_user)
    return SecurityIncidentResponse.model_validate(incident)


@router.patch(
    "/security/incidents/{incident_id}",
    response_model=SecurityIncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update security incident status, assignment, and resolution notes",
)
def update_security_incident(
    incident_id: str,
    request: SecurityIncidentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> SecurityIncidentResponse:
    """Triage or resolve a security incident."""
    try:
        updated = security_monitoring_service.update_incident(
            db=db,
            incident_id=incident_id,
            request=request,
            current_user=current_user,
        )
        return SecurityIncidentResponse.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/security/scan",
    response_model=SecurityScanResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger on-demand proactive security anomaly and threat scan",
)
def run_security_scan(
    lookback_minutes: int = Query(60, ge=5, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> SecurityScanResult:
    """Scan recent access logs for anomalous behavior."""
    return security_monitoring_service.scan_and_detect_anomalies(db, lookback_minutes=lookback_minutes)


# ============================================================================
# COMPLIANCE, RETENTION & LEGAL HOLDS
# ============================================================================

@router.get(
    "/security/compliance/summary",
    response_model=ComplianceSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve system compliance score, integrity health, and metrics",
)
def get_compliance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> ComplianceSummaryResponse:
    """Get system compliance summary."""
    return compliance_reporting_service.get_compliance_summary(db)


@router.get(
    "/security/retention/policies",
    response_model=list[DataRetentionPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="List regulatory data retention schedules",
)
def get_retention_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[DataRetentionPolicyResponse]:
    """List data retention policies."""
    policies = compliance_reporting_service.list_retention_policies(db)
    return [DataRetentionPolicyResponse.model_validate(p) for p in policies]


@router.post(
    "/security/retention/policies",
    response_model=DataRetentionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update regulatory data retention schedule",
)
def create_retention_policy(
    request: DataRetentionPolicyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DataRetentionPolicyResponse:
    """Create retention policy."""
    policy = compliance_reporting_service.create_retention_policy(db, request, current_user)
    return DataRetentionPolicyResponse.model_validate(policy)


@router.get(
    "/security/holds",
    response_model=list[LegalClinicalHoldResponse],
    status_code=status.HTTP_200_OK,
    summary="List active or released clinical and legal holds",
)
def list_legal_holds(
    status_filter: Optional[str] = Query(None, alias="status"),
    patient_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[LegalClinicalHoldResponse]:
    """List legal holds."""
    holds = compliance_reporting_service.list_legal_holds(db, status=status_filter, patient_id=patient_id)
    return [LegalClinicalHoldResponse.model_validate(h) for h in holds]


@router.post(
    "/security/holds",
    response_model=LegalClinicalHoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an immutable legal/clinical hold on records",
)
def place_legal_hold(
    request: LegalClinicalHoldCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> LegalClinicalHoldResponse:
    """Place legal/clinical hold."""
    hold = compliance_reporting_service.place_legal_hold(db, request, current_user)
    return LegalClinicalHoldResponse.model_validate(hold)


@router.post(
    "/security/holds/{hold_id}/release",
    response_model=LegalClinicalHoldResponse,
    status_code=status.HTTP_200_OK,
    summary="Release an active legal/clinical hold",
)
def release_legal_hold(
    hold_id: str,
    request: LegalClinicalHoldReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> LegalClinicalHoldResponse:
    """Release legal hold."""
    try:
        released = compliance_reporting_service.release_legal_hold(db, hold_id, request, current_user)
        return LegalClinicalHoldResponse.model_validate(released)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ============================================================================
# ASYNC BACKGROUND TASKS
# ============================================================================

@router.post(
    "/tasks/security/audit-integrity",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background audit trail hash chain integrity verification",
)
def enqueue_audit_integrity_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> BackgroundTaskResponse:
    """Enqueue audit verification task."""
    task = enqueue_audit_integrity_task(db=db, current_user=current_user)
    return _build_task_response(task)


@router.post(
    "/tasks/security/anomaly-scan",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background security threat and anomaly scan",
)
def enqueue_security_threat_scan(
    lookback_minutes: int = Query(60, ge=5, le=1440),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> BackgroundTaskResponse:
    """Enqueue anomaly scan task."""
    task = enqueue_security_scan_task(db=db, current_user=current_user, lookback_minutes=lookback_minutes)
    return _build_task_response(task)


@router.post(
    "/tasks/security/compliance-report",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background compliance summary calculation",
)
def enqueue_compliance_report_job(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> BackgroundTaskResponse:
    """Enqueue compliance report task."""
    task = enqueue_compliance_report_task(db=db, current_user=current_user)
    return _build_task_response(task)

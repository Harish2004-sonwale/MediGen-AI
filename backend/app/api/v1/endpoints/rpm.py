"""REST API Router for Remote Patient Monitoring (RPM), PROMs & Telehealth Protocols.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    require_role,
)

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.rpm import (
    PROMDefinitionListResponse,
    PROMDefinitionResponse,
    PROMResponseDetail,
    PROMResponseListResponse,
    PROMResponseSubmitRequest,
    RPMDeviceCreate,
    RPMDeviceListResponse,
    RPMDeviceResponse,
    RPMEscalationAcknowledgeRequest,
    RPMEscalationAlertListResponse,
    RPMEscalationAlertResponse,
    RPMEscalationResolveRequest,
    RPMObservationCreate,
    RPMObservationListResponse,
    RPMObservationResponse,
    RPMProgramEnrollRequest,
    RPMProgramListResponse,
    RPMProgramResponse,
    RPMTelemetrySummary,
    TelehealthSessionCreate,
    TelehealthSessionListResponse,
    TelehealthSessionResponse,
    TelehealthSessionUpdate,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType
from app.services.rpm_service import (
    acknowledge_escalation_alert,
    enroll_patient_in_rpm,
    get_patient_telemetry_summary,
    get_telehealth_session,
    ingest_observation,
    list_devices,
    list_escalation_alerts,
    list_observations,
    list_prom_definitions,
    list_prom_responses,
    list_rpm_programs,
    list_telehealth_sessions,
    register_device,
    resolve_escalation_alert,
    schedule_telehealth_session,
    submit_prom_response,
    update_telehealth_session,
)
from app.services.task_service import get_background_task_provider

router = APIRouter()


# ==============================================================================
# RPM PROGRAMS & DEVICES
# ==============================================================================

@router.post(
    "/programs/enroll",
    response_model=RPMProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a patient in a clinical Remote Patient Monitoring protocol",
)
def enroll_patient(
    payload: RPMProgramEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMProgramResponse:
    """Enroll a patient into an RPM program (Physician, Staff, or Admin)."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot self-enroll in RPM protocols without clinical order.",
        )
    try:
        return enroll_patient_in_rpm(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/programs",
    response_model=RPMProgramListResponse,
    status_code=status.HTTP_200_OK,
    summary="List RPM programs with patient isolation",
)
def get_programs(
    patient_id: Optional[str] = Query(None, description="Filter by patient identifier"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by program status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMProgramListResponse:
    """List RPM programs for authorized patients."""
    try:
        items, total = list_rpm_programs(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        return RPMProgramListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/devices",
    response_model=RPMDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register and assign a connected medical device",
)
def create_device(
    payload: RPMDeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMDeviceResponse:
    """Register a new RPM device/wearable."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device registration requires clinical or administrative authorization.",
        )
    try:
        return register_device(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/devices",
    response_model=RPMDeviceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered RPM devices with patient isolation",
)
def get_devices(
    patient_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMDeviceListResponse:
    """List registered devices with strict RBAC."""
    try:
        items, total = list_devices(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            device_type=device_type,
            skip=skip,
            limit=limit,
        )
        return RPMDeviceListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# RPM OBSERVATION INGESTION & SUMMARY
# ==============================================================================

@router.post(
    "/observations",
    response_model=RPMObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a remote physiological observation or telemetry stream",
)
def create_observation(
    payload: RPMObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMObservationResponse:
    """Ingest observation with deterministic threshold and escalation evaluation."""
    try:
        return ingest_observation(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/observations",
    response_model=RPMObservationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List remote monitoring observations with patient isolation",
)
def get_observations(
    patient_id: Optional[str] = Query(None),
    observation_type: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMObservationListResponse:
    """List RPM observations with classification filtering."""
    try:
        items, total = list_observations(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            observation_type=observation_type,
            classification=classification,
            skip=skip,
            limit=limit,
        )
        return RPMObservationListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/summary",
    response_model=RPMTelemetrySummary,
    status_code=status.HTTP_200_OK,
    summary="Retrieve aggregate RPM telemetry and trend summary for a patient",
)
def get_patient_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMTelemetrySummary:
    """Get aggregated patient telemetry and out-of-range metrics."""
    try:
        return get_patient_telemetry_summary(db, current_user, patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


# ==============================================================================
# RPM ESCALATION ALERTS
# ==============================================================================

@router.get(
    "/alerts",
    response_model=RPMEscalationAlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="List RPM escalation alerts",
)
def get_alerts(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMEscalationAlertListResponse:
    """List RPM escalation alerts with patient isolation."""
    try:
        items, total = list_escalation_alerts(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        return RPMEscalationAlertListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=RPMEscalationAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge an RPM escalation alert",
)
def acknowledge_alert(
    alert_id: str,
    payload: RPMEscalationAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMEscalationAlertResponse:
    """Clinician acknowledgment of RPM escalation alert."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients cannot acknowledge clinical escalation alerts.")
    try:
        return acknowledge_escalation_alert(db, current_user, alert_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=RPMEscalationAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve an RPM escalation alert with clinical documentation",
)
def resolve_alert(
    alert_id: str,
    payload: RPMEscalationResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RPMEscalationAlertResponse:
    """Clinician resolution of RPM escalation alert."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients cannot resolve clinical escalation alerts.")
    try:
        return resolve_escalation_alert(db, current_user, alert_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# PATIENT-REPORTED OUTCOMES (PROMS)
# ==============================================================================

@router.get(
    "/proms/definitions",
    response_model=PROMDefinitionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List standardized PROM survey questionnaire templates",
)
def get_prom_definitions(
    domain: Optional[str] = Query(None, description="Filter by domain e.g. mental_health, quality_of_life"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PROMDefinitionListResponse:
    """List active PROM questionnaire templates."""
    items = list_prom_definitions(db, domain)
    return PROMDefinitionListResponse(items=items, total=len(items))


@router.post(
    "/proms/responses",
    response_model=PROMResponseDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Submit patient PROM questionnaire response with deterministic scoring",
)
def submit_prom(
    payload: PROMResponseSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PROMResponseDetail:
    """Submit PROM survey response."""
    try:
        return submit_prom_response(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/proms/responses",
    response_model=PROMResponseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical PROM responses with patient isolation",
)
def get_prom_responses(
    patient_id: Optional[str] = Query(None),
    prom_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PROMResponseListResponse:
    """List PROM responses with patient isolation."""
    try:
        items, total = list_prom_responses(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            prom_id=prom_id,
            skip=skip,
            limit=limit,
        )
        return PROMResponseListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# TELEHEALTH & VIRTUAL CARE SESSIONS
# ==============================================================================

@router.post(
    "/telehealth/sessions",
    response_model=TelehealthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a telehealth virtual consultation session",
)
def schedule_session(
    payload: TelehealthSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TelehealthSessionResponse:
    """Schedule a telehealth session and generate pre-visit clinical briefing."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Telehealth scheduling must be initiated by clinical staff or through appointment booking.",
        )
    try:
        return schedule_telehealth_session(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/telehealth/sessions",
    response_model=TelehealthSessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List telehealth virtual consultations with patient isolation",
)
def get_sessions(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TelehealthSessionListResponse:
    """List telehealth sessions with strict RBAC."""
    try:
        items, total = list_telehealth_sessions(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        return TelehealthSessionListResponse(items=items, total=total)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/telehealth/sessions/{session_id}",
    response_model=TelehealthSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve telehealth session details and pre-visit clinical briefing",
)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TelehealthSessionResponse:
    """Get telehealth session details."""
    try:
        return get_telehealth_session(db, current_user, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch(
    "/telehealth/sessions/{session_id}",
    response_model=TelehealthSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update telehealth session lifecycle, clinical notes, or follow-up actions",
)
def update_session(
    session_id: str,
    payload: TelehealthSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TelehealthSessionResponse:
    """Update telehealth session."""
    if current_user.role == UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patients cannot modify telehealth session clinical records.")
    try:
        return update_telehealth_session(db, current_user, session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# ASYNCHRONOUS BACKGROUND TASKS
# ==============================================================================

@router.post(
    "/tasks/observations/process",
    response_model=BackgroundTask,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background RPM observation telemetry evaluation",
)
def enqueue_observation_processing(
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTask:
    """Enqueue background RPM processing."""
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.RPM_OBSERVATION_PROCESSING,
        fn=lambda p_id=patient_id: {"status": "completed", "patient_id": p_id},
        patient_id=patient_id,
        created_by_user_id=current_user.id,
    )
    return task

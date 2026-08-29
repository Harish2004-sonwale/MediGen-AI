"""API endpoints for Vital Telemetry Ingestion, CDS Alerting & Simulation.

Phase 9.0.9: Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion.
Provides:
- POST /api/v1/patients/{patient_id}/vitals          (Ingest vital reading & evaluate alerts)
- GET  /api/v1/patients/{patient_id}/vitals          (List historical vital readings)
- GET  /api/v1/patients/{patient_id}/vitals/latest   (Get latest vital snapshot)
- POST /api/v1/patients/{patient_id}/vitals/simulate (Ingest simulated telemetry)
- GET  /api/v1/patients/{patient_id}/alerts          (List patient CDS alerts)
- POST /api/v1/alerts/{alert_id}/acknowledge         (Clinician acknowledgement)
- POST /api/v1/alerts/{alert_id}/dismiss             (Clinician dismissal)
- GET  /api/v1/alerts/{alert_id}                     (Get alert details)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertDismissRequest,
    ClinicalAlertListResponse,
    ClinicalAlertResponse,
)
from app.schemas.vital import (
    VitalSimulateRequest,
    VitalTelemetryCreate,
    VitalTelemetryListResponse,
    VitalTelemetryResponse,
)
from app.services.vital_service import (
    acknowledge_clinical_alert,
    dismiss_clinical_alert,
    get_clinical_alert,
    get_latest_patient_vital,
    ingest_vital_telemetry,
    list_patient_alerts,
    list_patient_vitals,
    simulate_vital_telemetry,
)

router = APIRouter(tags=["Vital Telemetry & CDS Alerting"])


@router.post(
    "/patients/{patient_id}/vitals",
    response_model=VitalTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new vital telemetry reading and evaluate CDS alert thresholds",
)
def ingest_vitals_endpoint(
    patient_id: str,
    vital_in: VitalTelemetryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> VitalTelemetryResponse:
    """Ingest a patient vital sign telemetry reading."""
    reading, _ = ingest_vital_telemetry(
        db=db,
        patient_id=patient_id,
        vital_in=vital_in,
        current_user=current_user,
    )
    return reading


@router.post(
    "/patients/{patient_id}/vitals/simulate",
    response_model=VitalTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest simulated telemetry reading for testing/clinical demo",
)
def simulate_vitals_endpoint(
    patient_id: str,
    sim_in: VitalSimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> VitalTelemetryResponse:
    """Ingest preset simulated vital telemetry profile."""
    reading, _ = simulate_vital_telemetry(
        db=db,
        patient_id=patient_id,
        sim_in=sim_in,
        current_user=current_user,
    )
    return reading


@router.get(
    "/patients/{patient_id}/vitals",
    response_model=VitalTelemetryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical vital telemetry readings for a patient",
)
def list_patient_vitals_endpoint(
    patient_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> VitalTelemetryListResponse:
    """List historical telemetry readings."""
    return list_patient_vitals(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/patients/{patient_id}/vitals/latest",
    response_model=Optional[VitalTelemetryResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve the most recent vital telemetry snapshot for a patient",
)
def get_latest_patient_vital_endpoint(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Optional[VitalTelemetryResponse]:
    """Retrieve the latest telemetry reading."""
    return get_latest_patient_vital(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/alerts",
    response_model=ClinicalAlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical decision support alerts for a patient",
)
def list_patient_alerts_endpoint(
    patient_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Optional status filter: active, acknowledged, dismissed, resolved"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalAlertListResponse:
    """List clinical decision support alerts for the patient."""
    return list_patient_alerts(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        status_filter=status_filter,
    )


@router.get(
    "/alerts/{alert_id}",
    response_model=ClinicalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve details of a specific clinical alert",
)
def get_alert_endpoint(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalAlertResponse:
    """Retrieve details of a specific alert."""
    return get_clinical_alert(
        db=db,
        alert_id=alert_id,
        current_user=current_user,
    )


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=ClinicalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge an active clinical alert",
)
def acknowledge_alert_endpoint(
    alert_id: str,
    ack_in: Optional[AlertAcknowledgeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> ClinicalAlertResponse:
    """Acknowledge an active clinical alert."""
    return acknowledge_clinical_alert(
        db=db,
        alert_id=alert_id,
        ack_in=ack_in or AlertAcknowledgeRequest(),
        current_user=current_user,
    )


@router.post(
    "/alerts/{alert_id}/dismiss",
    response_model=ClinicalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Dismiss a clinical alert with a mandatory clinical justification",
)
def dismiss_alert_endpoint(
    alert_id: str,
    dismiss_in: AlertDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> ClinicalAlertResponse:
    """Dismiss a clinical alert with required reason."""
    return dismiss_clinical_alert(
        db=db,
        alert_id=alert_id,
        dismiss_in=dismiss_in,
        current_user=current_user,
    )

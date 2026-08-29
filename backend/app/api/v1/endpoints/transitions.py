"""API endpoints for Clinical Transitions of Care, Handoffs (I-PASS/SBAR) & Discharge Protocols.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.discharge import (
    DischargeProtocolCreate,
    DischargeProtocolListResponse,
    DischargeProtocolResponse,
    DischargeProtocolSynthesizeRequest,
    DischargeProtocolUpdate,
    DischargeSignoffRequest,
    DischargeStatus,
)
from app.schemas.handoff import (
    HandoffAcknowledge,
    HandoffCreate,
    HandoffListResponse,
    HandoffResponse,
    HandoffStatus,
    HandoffSynthesizeRequest,
    HandoffUpdate,
)
from app.schemas.task import BackgroundTaskResponse
from app.services import handoff_service

router = APIRouter(tags=["Transitions of Care & Discharge Protocols"])


# ==============================================================================
# CLINICAL HANDOFF ENDPOINTS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/handoffs",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or synthesize structured clinical shift handoff",
)
def create_clinical_handoff(
    patient_id: str,
    payload: HandoffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffResponse:
    """Create a structured clinical shift/transfer handoff using I-PASS or SBAR."""
    return handoff_service.create_handoff(db, patient_id, payload, current_user)


@router.post(
    "/patients/{patient_id}/handoffs/synthesize",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Synthesize assistive AI clinical handoff in draft status",
)
def synthesize_clinical_handoff(
    patient_id: str,
    payload: HandoffSynthesizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffResponse:
    """Synthesize structured I-PASS / SBAR handoff from patient encounters, vitals, alerts, and risk profile."""
    return handoff_service.synthesize_handoff(db, patient_id, payload, current_user)


@router.get(
    "/patients/{patient_id}/handoffs",
    response_model=HandoffListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical handoffs for a patient",
)
def list_patient_handoffs(
    patient_id: str,
    status_filter: Optional[HandoffStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffListResponse:
    """List historical clinical handoffs for a patient."""
    return handoff_service.list_patient_handoffs(db, patient_id, current_user, status_filter)


@router.get(
    "/handoffs/{handoff_id}",
    response_model=HandoffResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve clinical handoff details",
)
def get_clinical_handoff(
    handoff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffResponse:
    """Retrieve details and action checklist for a specific clinical handoff."""
    return handoff_service.get_handoff(db, handoff_id, current_user)


@router.patch(
    "/handoffs/{handoff_id}",
    response_model=HandoffResponse,
    status_code=status.HTTP_200_OK,
    summary="Update clinical handoff",
)
def update_clinical_handoff(
    handoff_id: str,
    payload: HandoffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffResponse:
    """Update action items, contingencies, or status of a clinical handoff."""
    return handoff_service.update_handoff(db, handoff_id, payload, current_user)


@router.post(
    "/handoffs/{handoff_id}/acknowledge",
    response_model=HandoffResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge clinical handoff with receiver read-back notes",
)
def acknowledge_clinical_handoff(
    handoff_id: str,
    payload: HandoffAcknowledge,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HandoffResponse:
    """Receiving clinician acknowledges handoff with formal synthesis notes."""
    return handoff_service.acknowledge_handoff(db, handoff_id, payload, current_user)


# ==============================================================================
# DISCHARGE PROTOCOL ENDPOINTS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/discharge-protocols",
    response_model=DischargeProtocolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create clinical discharge protocol",
)
def create_discharge_protocol(
    patient_id: str,
    payload: DischargeProtocolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolResponse:
    """Create a multi-disciplinary clinical discharge protocol."""
    return handoff_service.create_discharge_protocol(db, patient_id, payload, current_user)


@router.post(
    "/patients/{patient_id}/discharge-protocols/synthesize",
    response_model=DischargeProtocolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Synthesize assistive AI discharge protocol in draft status",
)
def synthesize_discharge_protocol(
    patient_id: str,
    payload: DischargeProtocolSynthesizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolResponse:
    """Synthesize complete discharge package with medication reconciliation and red flags."""
    return handoff_service.synthesize_discharge_protocol(db, patient_id, payload, current_user)


@router.get(
    "/patients/{patient_id}/discharge-protocols",
    response_model=DischargeProtocolListResponse,
    status_code=status.HTTP_200_OK,
    summary="List discharge protocols for a patient",
)
def list_patient_discharge_protocols(
    patient_id: str,
    status_filter: Optional[DischargeStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolListResponse:
    """List historical discharge protocols for a patient."""
    return handoff_service.list_patient_discharge_protocols(db, patient_id, current_user, status_filter)


@router.get(
    "/discharge-protocols/{discharge_id}",
    response_model=DischargeProtocolResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve discharge protocol details",
)
def get_discharge_protocol(
    discharge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolResponse:
    """Retrieve full discharge instructions and medication reconciliation breakdown."""
    return handoff_service.get_discharge_protocol(db, discharge_id, current_user)


@router.patch(
    "/discharge-protocols/{discharge_id}",
    response_model=DischargeProtocolResponse,
    status_code=status.HTTP_200_OK,
    summary="Update discharge protocol instructions or status",
)
def update_discharge_protocol(
    discharge_id: str,
    payload: DischargeProtocolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolResponse:
    """Update medications, follow-up instructions, or red flags in discharge protocol."""
    return handoff_service.update_discharge_protocol(db, discharge_id, payload, current_user)


@router.post(
    "/discharge-protocols/{discharge_id}/signoff",
    response_model=DischargeProtocolResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-disciplinary signoff for discharge protocol",
)
def signoff_discharge_protocol(
    discharge_id: str,
    payload: DischargeSignoffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DischargeProtocolResponse:
    """Attending Physician, Registered Nurse, or Pharmacist legal signoff."""
    return handoff_service.signoff_discharge_protocol(db, discharge_id, payload, current_user)


# ==============================================================================
# BACKGROUND TASK DISPATCH ENDPOINTS
# ==============================================================================

@router.post(
    "/tasks/patients/{patient_id}/handoff/synthesize",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background AI handoff synthesis task",
)
def enqueue_handoff_task(
    patient_id: str,
    payload: HandoffSynthesizeRequest,
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue an asynchronous background worker task to synthesize a clinical handoff."""
    task = handoff_service.enqueue_handoff_synthesis(patient_id, payload, current_user)
    return BackgroundTaskResponse.model_validate(task)


@router.post(
    "/tasks/patients/{patient_id}/discharge/synthesize",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background AI discharge protocol synthesis task",
)
def enqueue_discharge_task(
    patient_id: str,
    payload: DischargeProtocolSynthesizeRequest,
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue an asynchronous background worker task to synthesize a discharge protocol."""
    task = handoff_service.enqueue_discharge_synthesis(patient_id, payload, current_user)
    return BackgroundTaskResponse.model_validate(task)

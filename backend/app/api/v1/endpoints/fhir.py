from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.fhir import (
    FHIRBatchImportResponse,
    FHIRBundle,
    FHIRCarePlan,
    FHIRCommunication,
    FHIRComposition,
    FHIRCondition,
    FHIREncounter,
    FHIRGroup,
    FHIRImportResult,
    FHIRMedicationStatement,
    FHIRObservation,
    FHIRPatient,
    FHIRRiskAssessment,
    FHIRTask,
)
from app.services.fhir_export_service import (
    export_care_plan_as_fhir,
    export_care_task_as_fhir,
    export_cohort_as_fhir_group,
    export_condition_as_fhir,
    export_discharge_as_fhir_composition,

    export_encounter_as_fhir,
    export_handoff_as_fhir_communication,
    export_medication_statement_as_fhir,
    export_observation_as_fhir,
    export_patient_as_fhir,
    export_patient_bundle_as_fhir,
    export_risk_assessment_as_fhir,
)


from app.services.fhir_import_service import (
    import_fhir_bundle,
    import_fhir_resource,
)

router = APIRouter(prefix="/fhir", tags=["FHIR R4 Interoperability"])


# ============================================================================
# FHIR EXPORT ENDPOINTS
# ============================================================================

@router.get(
    "/Patient/{patient_id}",
    response_model=FHIRPatient,
    status_code=status.HTTP_200_OK,
    summary="Export patient demographics as FHIR R4 Patient resource",
)
def get_fhir_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRPatient:
    """Retrieve and export an authoritative patient record as a standard FHIR R4 Patient resource."""
    try:
        return export_patient_as_fhir(db, current_user, patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Encounter/{encounter_id}",
    response_model=FHIREncounter,
    status_code=status.HTTP_200_OK,
    summary="Export clinical encounter as FHIR R4 Encounter resource",
)
def get_fhir_encounter(
    encounter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIREncounter:
    """Retrieve and export an authoritative clinical encounter as a standard FHIR R4 Encounter resource."""
    try:
        return export_encounter_as_fhir(db, current_user, encounter_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Condition/{condition_id}",
    response_model=FHIRCondition,
    status_code=status.HTTP_200_OK,
    summary="Export clinical diagnosis as FHIR R4 Condition resource",
)
def get_fhir_condition(
    condition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRCondition:
    """Retrieve and export a clinical diagnosis condition as a standard FHIR R4 Condition resource."""
    try:
        return export_condition_as_fhir(db, current_user, condition_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/MedicationStatement/{medication_id}",
    response_model=FHIRMedicationStatement,
    status_code=status.HTTP_200_OK,
    summary="Export medication history as FHIR R4 MedicationStatement resource",
)
def get_fhir_medication(
    medication_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRMedicationStatement:
    """Retrieve and export a patient medication history item as a FHIR R4 MedicationStatement resource."""
    try:
        return export_medication_statement_as_fhir(db, current_user, medication_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Observation/{observation_id}",
    response_model=FHIRObservation,
    status_code=status.HTTP_200_OK,
    summary="Export clinical observation/lab result as FHIR R4 Observation resource",
)
def get_fhir_observation(
    observation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRObservation:
    """Retrieve and export a clinical observation/lab result as a FHIR R4 Observation resource."""
    try:
        return export_observation_as_fhir(db, current_user, observation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/bundle",
    response_model=FHIRBundle,
    status_code=status.HTTP_200_OK,
    summary="Export all patient clinical history as a FHIR R4 Bundle",
)
def get_fhir_patient_bundle(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRBundle:
    """Export complete patient clinical records (Patient, Encounters, Conditions, Medications, Observations) as a FHIR R4 Bundle."""
    try:
        return export_patient_bundle_as_fhir(db, current_user, patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/CarePlan/{care_plan_id}",
    response_model=FHIRCarePlan,
    status_code=status.HTTP_200_OK,
    summary="Export clinical care plan as a FHIR R4 CarePlan resource",
)
def get_fhir_care_plan(
    care_plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRCarePlan:
    """Retrieve and export a care plan as a standard FHIR R4 CarePlan resource."""
    try:
        return export_care_plan_as_fhir(db, current_user, care_plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Task/{task_id}",
    response_model=FHIRTask,
    status_code=status.HTTP_200_OK,
    summary="Export clinical care task as a FHIR R4 Task resource",
)
def get_fhir_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRTask:
    """Retrieve and export a care task as a standard FHIR R4 Task resource."""
    try:
        return export_care_task_as_fhir(db, current_user, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Group/{cohort_id}",
    response_model=FHIRGroup,
    status_code=status.HTTP_200_OK,
    summary="Export patient cohort / disease registry as a FHIR R4 Group resource",
)
def get_fhir_group(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRGroup:
    """Retrieve and export a cohort registry as a standard FHIR R4 Group resource."""
    try:
        return export_cohort_as_fhir_group(db, current_user, cohort_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/RiskAssessment/{assessment_id}",
    response_model=FHIRRiskAssessment,
    status_code=status.HTTP_200_OK,
    summary="Export clinical risk assessment as a FHIR R4 RiskAssessment resource",
)
def get_fhir_risk_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRRiskAssessment:
    """Retrieve and export a risk assessment as a standard FHIR R4 RiskAssessment resource."""
    try:
        return export_risk_assessment_as_fhir(db, current_user, assessment_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Composition/{discharge_id}",
    response_model=FHIRComposition,
    status_code=status.HTTP_200_OK,
    summary="Export clinical discharge protocol as a FHIR R4 Composition resource",
)
def get_fhir_composition(
    discharge_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRComposition:
    """Retrieve and export a discharge summary protocol as a standard FHIR R4 Composition resource."""
    try:
        return export_discharge_as_fhir_composition(db, current_user, discharge_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Communication/{handoff_id}",
    response_model=FHIRCommunication,
    status_code=status.HTTP_200_OK,
    summary="Export clinical handoff as a FHIR R4 Communication resource",
)
def get_fhir_communication(
    handoff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRCommunication:
    """Retrieve and export a clinical shift handoff as a standard FHIR R4 Communication resource."""
    try:
        return export_handoff_as_fhir_communication(db, current_user, handoff_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc



# ============================================================================
# FHIR IMPORT ENDPOINTS
# ============================================================================


@router.post(
    "/import",
    response_model=FHIRImportResult,
    status_code=status.HTTP_200_OK,
    summary="Import and persist a single FHIR R4 resource into MediGen-AI",
)
def import_single_resource(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRImportResult:
    """Validate, map, and import a single FHIR R4 resource (Patient, Encounter, Condition, MedicationStatement, Observation)."""
    try:
        result = import_fhir_resource(db, current_user, payload)
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/Bundle",
    response_model=FHIRBatchImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import a FHIR R4 Bundle containing multiple resources",
)
def import_bundle(
    bundle_payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRBatchImportResponse:
    """Import multiple FHIR resources packaged within a FHIR R4 Bundle."""
    try:
        return import_fhir_bundle(db, current_user, bundle_payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

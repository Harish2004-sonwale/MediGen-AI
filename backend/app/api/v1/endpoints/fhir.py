from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.fhir import (
    FHIRBatchImportResponse,
    FHIRBundle,
    FHIRCondition,
    FHIREncounter,
    FHIRImportResult,
    FHIRMedicationStatement,
    FHIRObservation,
    FHIRPatient,
)
from app.services.fhir_export_service import (
    export_condition_as_fhir,
    export_encounter_as_fhir,
    export_medication_statement_as_fhir,
    export_observation_as_fhir,
    export_patient_as_fhir,
    export_patient_bundle_as_fhir,
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

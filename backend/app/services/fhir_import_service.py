import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.fhir_validator import get_fhir_validator
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.schemas.fhir import (
    FHIRBatchImportResponse,
    FHIRImportResult,
    FHIRResourceType,
)
from app.schemas.user import UserRole
from app.services.appointment_service import resolve_patient
from app.services.encounter_service import create_encounter, get_encounter_by_encounter_id
from app.services.fhir_mapper_service import FHIREncounterMapper, FHIRPatientMapper
from app.services.patient_service import (
    create_patient,
    get_patient_by_patient_id,
    update_patient,
)
from app.services.rag_service import validate_patient_rag_access

logger = logging.getLogger(__name__)


def import_fhir_resource(
    db: Session,
    current_user: User,
    resource_data: dict[str, Any],
) -> FHIRImportResult:
    """Import and persist a single FHIR R4 resource into MediGen-AI authoritative storage."""
    validator = get_fhir_validator()
    validation_report = validator.validate_resource(resource_data)

    if not validation_report.is_valid:
        return FHIRImportResult(
            success=False,
            resource_type=validation_report.resource_type or "Unknown",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message="FHIR validation failed.",
            validation_errors=validation_report.errors,
        )

    resource_type = resource_data.get("resourceType")

    try:
        if resource_type == FHIRResourceType.PATIENT.value:
            return _import_patient(db, current_user, resource_data)
        elif resource_type == FHIRResourceType.ENCOUNTER.value:
            return _import_encounter(db, current_user, resource_data)
        elif resource_type == FHIRResourceType.CONDITION.value:
            return _import_condition(db, current_user, resource_data)
        elif resource_type == FHIRResourceType.MEDICATION_STATEMENT.value:
            return _import_medication_statement(db, current_user, resource_data)
        elif resource_type == FHIRResourceType.OBSERVATION.value:
            return _import_observation(db, current_user, resource_data)
        else:
            return FHIRImportResult(
                success=False,
                resource_type=str(resource_type),
                resource_id=resource_data.get("id"),
                internal_id=None,
                status="failed",
                message=f"Import not supported for resourceType '{resource_type}'.",
            )
    except PermissionError as perm_err:
        raise perm_err
    except Exception as exc:
        logger.exception("Error during FHIR resource import")
        return FHIRImportResult(
            success=False,
            resource_type=str(resource_type),
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message=f"Import failed: {str(exc)}",
            validation_errors=[str(exc)],
        )


def _import_patient(db: Session, current_user: User, resource_data: dict[str, Any]) -> FHIRImportResult:
    """Import FHIR Patient resource."""
    patient_create = FHIRPatientMapper.to_internal(resource_data)
    patient_id_candidate = resource_data.get("id")

    existing_patient = None
    if patient_id_candidate:
        existing_patient = get_patient_by_patient_id(db, patient_id_candidate)

    if existing_patient:
        validate_patient_rag_access(db, current_user, existing_patient)
        from app.schemas.patient import PatientUpdate

        update_data = PatientUpdate(
            first_name=patient_create.first_name,
            last_name=patient_create.last_name,
            phone=patient_create.phone,
            email=patient_create.email,
            address=patient_create.address,
            emergency_contact_name=patient_create.emergency_contact_name,
            emergency_contact_phone=patient_create.emergency_contact_phone,
            status=patient_create.status,
        )
        updated = update_patient(db, existing_patient, update_data)
        return FHIRImportResult(
            success=True,
            resource_type="Patient",
            resource_id=resource_data.get("id"),
            internal_id=updated.patient_id if updated else existing_patient.patient_id,
            status="updated",
            message=f"Patient record updated for {existing_patient.patient_id}.",
        )

    if current_user.role not in (UserRole.ADMIN, UserRole.HEALTHCARE_STAFF, UserRole.DOCTOR):
        raise PermissionError("Only clinical staff or administrators can register new patient records via FHIR import.")

    new_patient = create_patient(db, patient_create)
    return FHIRImportResult(
        success=True,
        resource_type="Patient",
        resource_id=resource_data.get("id"),
        internal_id=new_patient.patient_id,
        status="created",
        message=f"Patient record created with ID {new_patient.patient_id}.",
    )


def _import_encounter(db: Session, current_user: User, resource_data: dict[str, Any]) -> FHIRImportResult:
    """Import FHIR Encounter resource."""
    encounter_create, target_patient_id = FHIREncounterMapper.to_internal(resource_data)

    if not target_patient_id:
        return FHIRImportResult(
            success=False,
            resource_type="Encounter",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message="Encounter resource must include a valid 'subject.reference' referencing a Patient (e.g. Patient/PAT-...).",
            validation_errors=["Missing or invalid subject.reference."],
        )

    patient = resolve_patient(db, target_patient_id)
    if not patient:
        return FHIRImportResult(
            success=False,
            resource_type="Encounter",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message=f"Referenced patient '{target_patient_id}' not found.",
            validation_errors=[f"Patient '{target_patient_id}' does not exist."],
        )

    validate_patient_rag_access(db, current_user, patient)

    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        raise PermissionError("Only clinical professionals or administrators can record clinical encounters.")

    enc_id_candidate = resource_data.get("id")
    if enc_id_candidate:
        existing_enc = get_encounter_by_encounter_id(db, enc_id_candidate)
        if existing_enc:
            return FHIRImportResult(
                success=True,
                resource_type="Encounter",
                resource_id=enc_id_candidate,
                internal_id=existing_enc.encounter_id,
                status="skipped",
                message=f"Encounter {existing_enc.encounter_id} already exists (idempotent no-op).",
            )

    encounter = create_encounter(
        db,
        patient_public_id=patient.patient_id,
        encounter_in=encounter_create,
        attending_user_id=current_user.id,
    )
    return FHIRImportResult(
        success=True,
        resource_type="Encounter",
        resource_id=resource_data.get("id"),
        internal_id=encounter.encounter_id,
        status="created",
        message=f"Encounter record created with ID {encounter.encounter_id}.",
    )


def _import_condition(db: Session, current_user: User, resource_data: dict[str, Any]) -> FHIRImportResult:
    """Import FHIR Condition resource by recording it as a clinical encounter assessment."""
    subject = resource_data.get("subject", {})
    patient_ref = subject.get("reference", "").split("/")[-1].strip()
    if not patient_ref:
        return FHIRImportResult(
            success=False,
            resource_type="Condition",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message="Condition resource must include a valid 'subject.reference' referencing a Patient.",
        )

    patient = resolve_patient(db, patient_ref)
    if not patient:
        return FHIRImportResult(
            success=False,
            resource_type="Condition",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message=f"Referenced patient '{patient_ref}' not found.",
        )

    validate_patient_rag_access(db, current_user, patient)

    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        raise PermissionError("Only clinical professionals or administrators can record diagnoses/conditions.")

    code_obj = resource_data.get("code", {})
    diag_title = code_obj.get("text")
    if not diag_title and code_obj.get("coding"):
        diag_title = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code")
    if not diag_title:
        notes = resource_data.get("note", [])
        if notes and isinstance(notes, list) and isinstance(notes[0], dict):
            diag_title = notes[0].get("text", "Imported Condition")
        else:
            diag_title = "Imported Condition"

    from app.schemas.encounter import EncounterCreate, EncounterType

    enc_in = EncounterCreate(
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint=f"Condition Record: {diag_title}",
        clinical_notes=f"Imported via FHIR R4 Condition resource (id: {resource_data.get('id', 'N/A')}).",
        assessment=diag_title,
        plan=None,
    )
    enc = create_encounter(db, patient_public_id=patient.patient_id, encounter_in=enc_in, attending_user_id=current_user.id)
    return FHIRImportResult(
        success=True,
        resource_type="Condition",
        resource_id=resource_data.get("id"),
        internal_id=f"COND-{enc.encounter_id}",
        status="created",
        message=f"Condition recorded via encounter {enc.encounter_id}.",
    )


def _import_medication_statement(db: Session, current_user: User, resource_data: dict[str, Any]) -> FHIRImportResult:
    """Import FHIR MedicationStatement resource."""
    subject = resource_data.get("subject", {})
    patient_ref = subject.get("reference", "").split("/")[-1].strip()
    if not patient_ref:
        return FHIRImportResult(
            success=False,
            resource_type="MedicationStatement",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message="MedicationStatement must include a valid 'subject.reference'.",
        )

    patient = resolve_patient(db, patient_ref)
    if not patient:
        return FHIRImportResult(
            success=False,
            resource_type="MedicationStatement",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message=f"Referenced patient '{patient_ref}' not found.",
        )

    validate_patient_rag_access(db, current_user, patient)

    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        raise PermissionError("Only clinical professionals or administrators can record medication statements.")

    med_obj = resource_data.get("medicationCodeableConcept", {})
    med_name = med_obj.get("text")
    if not med_name and med_obj.get("coding"):
        med_name = med_obj["coding"][0].get("display") or med_obj["coding"][0].get("code")
    if not med_name:
        med_name = "Prescribed Medication"

    from app.schemas.encounter import EncounterCreate, EncounterType

    enc_in = EncounterCreate(
        encounter_type=EncounterType.FOLLOW_UP,
        chief_complaint=f"Medication Record: {med_name}",
        clinical_notes=f"Imported via FHIR R4 MedicationStatement (id: {resource_data.get('id', 'N/A')}). Status: {resource_data.get('status', 'active')}.",
        plan=f"Prescribed: {med_name}",
    )
    enc = create_encounter(db, patient_public_id=patient.patient_id, encounter_in=enc_in, attending_user_id=current_user.id)
    return FHIRImportResult(
        success=True,
        resource_type="MedicationStatement",
        resource_id=resource_data.get("id"),
        internal_id=f"MED-{enc.encounter_id}",
        status="created",
        message=f"Medication recorded via encounter {enc.encounter_id}.",
    )


def _import_observation(db: Session, current_user: User, resource_data: dict[str, Any]) -> FHIRImportResult:
    """Import FHIR Observation resource."""
    subject = resource_data.get("subject", {})
    patient_ref = subject.get("reference", "").split("/")[-1].strip()
    if not patient_ref:
        return FHIRImportResult(
            success=False,
            resource_type="Observation",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message="Observation must include a valid 'subject.reference'.",
        )

    patient = resolve_patient(db, patient_ref)
    if not patient:
        return FHIRImportResult(
            success=False,
            resource_type="Observation",
            resource_id=resource_data.get("id"),
            internal_id=None,
            status="failed",
            message=f"Referenced patient '{patient_ref}' not found.",
        )

    validate_patient_rag_access(db, current_user, patient)

    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        raise PermissionError("Only clinical professionals or administrators can record observation findings.")

    code_obj = resource_data.get("code", {})
    test_name = code_obj.get("text")
    if not test_name and code_obj.get("coding"):
        test_name = code_obj["coding"][0].get("display") or code_obj["coding"][0].get("code")
    if not test_name:
        test_name = "Clinical Observation"

    val_str = resource_data.get("valueString")
    if not val_str and resource_data.get("valueQuantity"):
        vq = resource_data["valueQuantity"]
        val_str = f"{vq.get('value', '')} {vq.get('unit', '')}".strip()

    from app.schemas.encounter import EncounterCreate, EncounterType

    enc_in = EncounterCreate(
        encounter_type=EncounterType.FOLLOW_UP,
        chief_complaint=f"Observation Record: {test_name}",
        clinical_notes=f"Imported via FHIR R4 Observation (id: {resource_data.get('id', 'N/A')}). Result: {val_str or 'N/A'}.",
        assessment=f"{test_name}: {val_str or 'Recorded'}",
    )
    enc = create_encounter(db, patient_public_id=patient.patient_id, encounter_in=enc_in, attending_user_id=current_user.id)
    return FHIRImportResult(
        success=True,
        resource_type="Observation",
        resource_id=resource_data.get("id"),
        internal_id=f"OBS-{enc.encounter_id}",
        status="created",
        message=f"Observation recorded via encounter {enc.encounter_id}.",
    )


def import_fhir_bundle(
    db: Session,
    current_user: User,
    bundle_data: dict[str, Any],
) -> FHIRBatchImportResponse:
    """Import a FHIR R4 Bundle containing multiple resources."""
    validator = get_fhir_validator()
    val_report = validator.validate_bundle(bundle_data)

    if not val_report.is_valid:
        return FHIRBatchImportResponse(
            success=False,
            imported=0,
            skipped=0,
            failed=1,
            results=[],
            errors=val_report.errors,
        )

    entries = bundle_data.get("entry", [])
    results: list[FHIRImportResult] = []
    imported_count = 0
    skipped_count = 0
    failed_count = 0

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        resource = entry.get("resource")
        if not resource:
            continue

        res_result = import_fhir_resource(db, current_user, resource)
        results.append(res_result)

        if res_result.status in ("created", "updated"):
            imported_count += 1
        elif res_result.status == "skipped":
            skipped_count += 1
        else:
            failed_count += 1

    overall_success = (failed_count == 0)
    return FHIRBatchImportResponse(
        success=overall_success,
        imported=imported_count,
        skipped=skipped_count,
        failed=failed_count,
        results=results,
        errors=[] if overall_success else [r.message for r in results if not r.success],
    )

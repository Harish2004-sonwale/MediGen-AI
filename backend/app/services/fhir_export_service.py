from datetime import datetime, timezone
import logging
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.schemas.fhir import (
    FHIRBundle,
    FHIRBundleEntry,
    FHIRCarePlan,
    FHIRCondition,
    FHIREncounter,
    FHIRMedicationStatement,
    FHIRObservation,
    FHIRPatient,
    FHIRTask,
)
from app.services.appointment_service import resolve_patient
from app.services.encounter_service import get_encounter_by_encounter_id
from app.services.fhir_mapper_service import (
    FHIRCarePlanMapper,
    FHIRConditionMapper,
    FHIREncounterMapper,
    FHIRMedicationStatementMapper,
    FHIRObservationMapper,
    FHIRPatientMapper,
    FHIRTaskMapper,
)
from app.services.rag_service import validate_patient_rag_access
from app.services.timeline_service import get_patient_timeline

logger = logging.getLogger(__name__)


def export_patient_as_fhir(db: Session, current_user: User, patient_id_str: str) -> FHIRPatient:
    """Export internal patient record as standard FHIR R4 Patient resource."""
    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise ValueError(f"Patient with identifier '{patient_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, patient)
    logger.info("Exporting FHIR Patient resource for patient=%s", patient.patient_id)
    return FHIRPatientMapper.to_fhir(patient)


def export_encounter_as_fhir(db: Session, current_user: User, encounter_id_str: str) -> FHIREncounter:
    """Export internal clinical encounter as standard FHIR R4 Encounter resource."""
    encounter = get_encounter_by_encounter_id(db, encounter_id_str)
    if not encounter:
        raise ValueError(f"Encounter with identifier '{encounter_id_str}' was not found.")

    patient = db.scalars(select(Patient).where(Patient.id == encounter.patient_id)).first()
    if not patient:
        raise ValueError("Associated patient record not found.")

    validate_patient_rag_access(db, current_user, patient)
    logger.info("Exporting FHIR Encounter resource encounter=%s for patient=%s", encounter.encounter_id, patient.patient_id)
    return FHIREncounterMapper.to_fhir(encounter, patient)


def _extract_patient_from_resource_id(db: Session, resource_id: str, prefix: str) -> Optional[Patient]:
    """Helper to extract and resolve Patient from compound resource IDs (e.g., MED-PAT-..., OBS-PAT-..., COND-...)."""
    p = resolve_patient(db, resource_id)
    if p:
        return p
    remainder = resource_id
    if resource_id.startswith(f"{prefix}-"):
        remainder = resource_id[len(prefix) + 1 :]
    p = resolve_patient(db, remainder)
    if p:
        return p
    if "-" in remainder:
        sub = remainder.rsplit("-", 1)[0]
        p = resolve_patient(db, sub)
        if p:
            return p
    all_patients = db.scalars(select(Patient)).all()
    for pat in all_patients:
        if pat.patient_id and pat.patient_id in resource_id:
            return pat
    return None


def export_condition_as_fhir(db: Session, current_user: User, condition_id_str: str) -> FHIRCondition:
    """Export a condition resource by condition ID."""
    enc_id = condition_id_str[5:] if condition_id_str.startswith("COND-") else condition_id_str
    enc = get_encounter_by_encounter_id(db, enc_id) or get_encounter_by_encounter_id(db, condition_id_str)
    if enc:
        patient = db.scalars(select(Patient).where(Patient.id == enc.patient_id)).first()
        if patient:
            validate_patient_rag_access(db, current_user, patient)
            return FHIRConditionMapper.to_fhir(
                condition_id=f"COND-{enc.encounter_id}",
                diagnosis_title=enc.assessment or enc.chief_complaint,
                patient_id=patient.patient_id,
                encounter_id=enc.encounter_id,
                clinical_status="active",
                recorded_date=enc.encounter_date,
                notes=enc.clinical_notes,
            )

    patient = _extract_patient_from_resource_id(db, condition_id_str, "COND")
    if not patient:
        raise ValueError(f"Condition with identifier '{condition_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, patient)
    return FHIRConditionMapper.to_fhir(
        condition_id=condition_id_str,
        diagnosis_title="Clinical Diagnosis",
        patient_id=patient.patient_id,
        clinical_status="active",
        recorded_date=datetime.now(timezone.utc),
    )


def export_medication_statement_as_fhir(db: Session, current_user: User, medication_id_str: str) -> FHIRMedicationStatement:
    """Export a MedicationStatement resource by medication ID."""
    patient = _extract_patient_from_resource_id(db, medication_id_str, "MED")

    if not patient:
        raise ValueError(f"MedicationStatement with identifier '{medication_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, patient)
    return FHIRMedicationStatementMapper.to_fhir(
        medication_id=medication_id_str,
        medication_name="Prescribed Medication",
        patient_id=patient.patient_id,
        status="active",
        effective_date=datetime.now(timezone.utc),
    )


def export_observation_as_fhir(db: Session, current_user: User, observation_id_str: str) -> FHIRObservation:
    """Export an Observation resource by observation ID."""
    patient = _extract_patient_from_resource_id(db, observation_id_str, "OBS")

    if not patient:
        raise ValueError(f"Observation with identifier '{observation_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, patient)
    return FHIRObservationMapper.to_fhir(
        observation_id=observation_id_str,
        test_name="Clinical Observation",
        patient_id=patient.patient_id,
        value_string="Recorded Observation",
        status="final",
        effective_date=datetime.now(timezone.utc),
    )


def export_patient_bundle_as_fhir(db: Session, current_user: User, patient_id_str: str) -> FHIRBundle:
    """Export all available patient records (Patient, Encounters, Conditions, Medications, Observations) as a FHIR R4 Bundle."""
    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise ValueError(f"Patient with identifier '{patient_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, patient)
    logger.info("Exporting complete FHIR R4 Bundle for patient=%s", patient.patient_id)

    entries: list[FHIRBundleEntry] = []

    # 1. Patient Resource
    fhir_patient = FHIRPatientMapper.to_fhir(patient)
    entries.append(
        FHIRBundleEntry(
            fullUrl=f"https://medigen.ai/fhir/Patient/{patient.patient_id}",
            resource=fhir_patient.model_dump(exclude_none=True),
        )
    )

    # 2. Encounter Resources
    encounters = db.scalars(
        select(Encounter).where(Encounter.patient_id == patient.id).order_by(Encounter.encounter_date.desc())
    ).all()

    for enc in encounters:
        fhir_enc = FHIREncounterMapper.to_fhir(enc, patient)
        entries.append(
            FHIRBundleEntry(
                fullUrl=f"https://medigen.ai/fhir/Encounter/{enc.encounter_id}",
                resource=fhir_enc.model_dump(exclude_none=True),
            )
        )

        if enc.assessment:
            cond_id = f"COND-{enc.encounter_id}"
            fhir_cond = FHIRConditionMapper.to_fhir(
                condition_id=cond_id,
                diagnosis_title=enc.assessment,
                patient_id=patient.patient_id,
                encounter_id=enc.encounter_id,
                clinical_status="active",
                recorded_date=enc.encounter_date,
                notes=enc.clinical_notes,
            )
            entries.append(
                FHIRBundleEntry(
                    fullUrl=f"https://medigen.ai/fhir/Condition/{cond_id}",
                    resource=fhir_cond.model_dump(exclude_none=True),
                )
            )

    # 3. Extract Timeline Derived Facts for Condition, MedicationStatement, and Observation
    timeline = get_patient_timeline(db, patient.patient_id, current_user, limit=100)
    for ev in timeline.events:
        if ev.event_type.value == "medication_prescribed":
            med_id = f"MED-{ev.event_id}"
            fhir_med = FHIRMedicationStatementMapper.to_fhir(
                medication_id=med_id,
                medication_name=ev.title.replace("Prescribed: ", ""),
                patient_id=patient.patient_id,
                status="active",
                effective_date=ev.event_date,
                notes=ev.description,
            )
            entries.append(
                FHIRBundleEntry(
                    fullUrl=f"https://medigen.ai/fhir/MedicationStatement/{med_id}",
                    resource=fhir_med.model_dump(exclude_none=True),
                )
            )
        elif ev.event_type.value == "lab_result":
            obs_id = f"OBS-{ev.event_id}"
            fhir_obs = FHIRObservationMapper.to_fhir(
                observation_id=obs_id,
                test_name=ev.title.replace("Lab Result: ", ""),
                patient_id=patient.patient_id,
                value_string=ev.description,
                status="final",
                effective_date=ev.event_date,
                notes=ev.description,
            )
            entries.append(
                FHIRBundleEntry(
                    fullUrl=f"https://medigen.ai/fhir/Observation/{obs_id}",
                    resource=fhir_obs.model_dump(exclude_none=True),
                )
            )

    return FHIRBundle(
        resourceType="Bundle",
        id=f"BUNDLE-{patient.patient_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        type="collection",
        timestamp=datetime.now(timezone.utc).isoformat(),
        total=len(entries),
        entry=entries,
    )


def export_care_plan_as_fhir(db: Session, current_user: User, plan_id_str: str) -> FHIRCarePlan:
    """Export internal clinical care plan as standard FHIR R4 CarePlan resource."""
    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id_str)
    plan = db.execute(stmt).scalar_one_or_none()
    if not plan:
        raise ValueError(f"Care plan with identifier '{plan_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, plan.patient)
    logger.info("Exporting FHIR CarePlan resource plan=%s for patient=%s", plan.plan_id, plan.patient.patient_id)
    return FHIRCarePlanMapper.to_fhir(plan, plan.patient.patient_id)


def export_care_task_as_fhir(db: Session, current_user: User, task_id_str: str) -> FHIRTask:
    """Export internal clinical care task as standard FHIR R4 Task resource."""
    stmt = select(CareTask).where(CareTask.task_id == task_id_str)
    task = db.execute(stmt).scalar_one_or_none()
    if not task:
        raise ValueError(f"Care task with identifier '{task_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, task.patient)
    logger.info("Exporting FHIR Task resource task=%s for patient=%s", task.task_id, task.patient.patient_id)
    return FHIRTaskMapper.to_fhir(task, task.patient.patient_id)

from datetime import datetime, timezone
import logging
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.cohort import CohortMembership, PatientCohort
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.imaging import ImagingAsset, ImagingFinding, ImagingStudy, RadiologyReport
from app.models.patient import Patient
from app.models.quality import QualityMeasure, QualityMeasureReport
from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.rpm import PROMDefinition, PROMResponse, RPMDevice, RPMObservation
from app.models.trials import BiomarkerObservation, ClinicalTrial, GenomicProfile
from app.models.agents import ClinicalAgentRecommendation, ClinicalAgentRun
from app.models.user import User, UserRole
from app.schemas.fhir import (
    FHIRBundle,
    FHIRBundleEntry,
    FHIRCarePlan,
    FHIRCommunication,
    FHIRComposition,
    FHIRCondition,
    FHIRDevice,
    FHIRDiagnosticReport,
    FHIREncounter,
    FHIRGroup,
    FHIRImagingStudy,
    FHIRMeasure,
    FHIRMeasureReport,
    FHIRMedicationStatement,
    FHIRObservation,
    FHIRPatient,
    FHIRProvenance,
    FHIRQuestionnaire,
    FHIRQuestionnaireResponse,
    FHIRResearchStudy,
    FHIRRiskAssessment,
    FHIRServiceRequest,
    FHIRTask,
)

from app.services.appointment_service import resolve_patient

from app.services.encounter_service import get_encounter_by_encounter_id
from app.services.fhir_mapper_service import (
    FHIRAgentProvenanceMapper,
    FHIRAgentRecommendationTaskMapper,
    FHIRBiomarkerObservationMapper,
    FHIRCarePlanMapper,
    FHIRCommunicationMapper,
    FHIRCompositionMapper,
    FHIRConditionMapper,
    FHIRDeviceMapper,
    FHIRDiagnosticReportMapper,
    FHIREncounterMapper,
    FHIRGenomicProfileMapper,
    FHIRGroupMapper,
    FHIRImagingObservationMapper,
    FHIRImagingStudyMapper,
    FHIRMeasureMapper,
    FHIRMeasureReportMapper,
    FHIRMedicationStatementMapper,
    FHIRObservationMapper,


    FHIRPatientMapper,
    FHIRQuestionnaireMapper,
    FHIRQuestionnaireResponseMapper,
    FHIRRadiologyReportMapper,
    FHIRResearchStudyMapper,
    FHIRRiskAssessmentMapper,
    FHIRServiceRequestMapper,
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


def export_cohort_as_fhir_group(db: Session, current_user: User, cohort_id_str: str) -> FHIRGroup:
    """Export internal patient cohort/registry as standard FHIR R4 Group resource."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise ValueError("Access denied: Insufficient privileges to export FHIR Group resource.")

    stmt = select(PatientCohort).where(
        (PatientCohort.cohort_id == cohort_id_str)
        | (PatientCohort.id == (int(cohort_id_str) if cohort_id_str.isdigit() else -1))
    )
    cohort = db.execute(stmt).scalar_one_or_none()
    if not cohort:
        raise ValueError(f"Patient cohort with identifier '{cohort_id_str}' was not found.")

    members = (
        db.execute(
            select(CohortMembership)
            .where(CohortMembership.cohort_id == cohort.id)
        )
        .scalars()
        .all()
    )

    logger.info("Exporting FHIR Group resource cohort=%s with %d members", cohort.cohort_id, len(members))
    return FHIRGroupMapper.to_fhir(cohort, members)


def export_risk_assessment_as_fhir(db: Session, current_user: User, assessment_id_str: str) -> FHIRRiskAssessment:
    """Export internal clinical risk assessment as standard FHIR R4 RiskAssessment resource."""
    stmt = select(ClinicalRiskAssessment).where(ClinicalRiskAssessment.assessment_id == assessment_id_str)
    assessment = db.execute(stmt).scalar_one_or_none()
    if not assessment:
        raise ValueError(f"Clinical risk assessment with identifier '{assessment_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, assessment.patient)
    logger.info(
        "Exporting FHIR RiskAssessment resource id=%s for patient=%s",
        assessment.assessment_id,
        assessment.patient.patient_id,
    )
    return FHIRRiskAssessmentMapper.to_fhir(assessment, assessment.patient.patient_id)


def export_discharge_as_fhir_composition(db: Session, current_user: User, discharge_id_str: str) -> FHIRComposition:
    """Export internal clinical discharge protocol as standard FHIR R4 Composition resource."""
    stmt = select(DischargeProtocol).where(DischargeProtocol.discharge_id == discharge_id_str)
    discharge = db.execute(stmt).scalar_one_or_none()
    if not discharge:
        raise ValueError(f"Discharge protocol with identifier '{discharge_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, discharge.patient)
    logger.info(
        "Exporting FHIR Composition resource id=%s for patient=%s",
        discharge.discharge_id,
        discharge.patient.patient_id,
    )
    return FHIRCompositionMapper.to_fhir(discharge, discharge.patient.patient_id)


def export_handoff_as_fhir_communication(db: Session, current_user: User, handoff_id_str: str) -> FHIRCommunication:
    """Export internal clinical handoff as standard FHIR R4 Communication resource."""
    stmt = select(ClinicalHandoff).where(ClinicalHandoff.handoff_id == handoff_id_str)
    handoff = db.execute(stmt).scalar_one_or_none()
    if not handoff:
        raise ValueError(f"Clinical handoff with identifier '{handoff_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, handoff.patient)
    logger.info(
        "Exporting FHIR Communication resource id=%s for patient=%s",
        handoff.handoff_id,
        handoff.patient.patient_id,
    )
    return FHIRCommunicationMapper.to_fhir(handoff, handoff.patient.patient_id)


def export_order_as_fhir_service_request(db: Session, current_user: User, order_id_str: str) -> FHIRServiceRequest:
    """Export internal clinical order as standard FHIR R4 ServiceRequest resource."""
    stmt = select(ClinicalOrder).where(ClinicalOrder.order_id == order_id_str)
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise ValueError(f"Clinical order with identifier '{order_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, order.patient)
    logger.info(
        "Exporting FHIR ServiceRequest resource id=%s for patient=%s",
        order.order_id,
        order.patient.patient_id,
    )
    return FHIRServiceRequestMapper.to_fhir(order, order.patient.patient_id)


def export_result_as_fhir_diagnostic_report(db: Session, current_user: User, result_id_str: str) -> FHIRDiagnosticReport:
    """Export internal diagnostic result as standard FHIR R4 DiagnosticReport resource."""
    stmt = select(DiagnosticResult).where(DiagnosticResult.result_id == result_id_str)
    result = db.execute(stmt).scalar_one_or_none()
    if not result:
        raise ValueError(f"Diagnostic result with identifier '{result_id_str}' was not found.")

    validate_patient_rag_access(db, current_user, result.patient)
    logger.info(
        "Exporting FHIR DiagnosticReport resource id=%s for patient=%s",
        result.result_id,
        result.patient.patient_id,
    )
    return FHIRDiagnosticReportMapper.to_fhir(result, result.patient.patient_id)


def export_quality_measure_as_fhir(db: Session, current_user: User, measure_id_str: str) -> FHIRMeasure:
    """Export internal quality measure definition as standard FHIR R4 Measure."""
    from app.services.quality_service import seed_default_measures
    seed_default_measures(db)

    stmt = select(QualityMeasure).where(QualityMeasure.measure_id == measure_id_str)
    measure = db.execute(stmt).scalar_one_or_none()
    if not measure:
        raise ValueError(f"Quality measure '{measure_id_str}' was not found.")

    logger.info("Exporting FHIR Measure resource id=%s", measure.measure_id)
    return FHIRMeasureMapper.to_fhir(measure)



def export_quality_report_as_fhir(db: Session, current_user: User, report_id_str: str) -> FHIRMeasureReport:
    """Export population compliance report as standard FHIR R4 MeasureReport."""
    stmt = select(QualityMeasureReport).where(QualityMeasureReport.report_id == report_id_str)
    report = db.execute(stmt).scalar_one_or_none()
    if not report:
        raise ValueError(f"Compliance report '{report_id_str}' was not found.")

    logger.info("Exporting FHIR MeasureReport resource id=%s", report.report_id)
    return FHIRMeasureReportMapper.to_fhir(report)


def export_device_as_fhir(db: Session, current_user: User, device_id_str: str) -> FHIRDevice:
    """Export registered RPM device as standard FHIR R4 Device."""
    stmt = select(RPMDevice).where(RPMDevice.device_id == device_id_str)
    device = db.execute(stmt).scalar_one_or_none()
    if not device:
        raise ValueError(f"Device '{device_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and device.patient and device.patient.email != current_user.email:
        raise PermissionError("Access denied to requested device.")

    logger.info("Exporting FHIR Device resource id=%s", device.device_id)
    return FHIRDeviceMapper.to_fhir(device)


def export_questionnaire_as_fhir(db: Session, current_user: User, prom_id_str: str) -> FHIRQuestionnaire:
    """Export standardized PROM survey as standard FHIR R4 Questionnaire."""
    from app.services.rpm_service import seed_default_prom_definitions
    seed_default_prom_definitions(db)

    stmt = select(PROMDefinition).where(PROMDefinition.prom_id == prom_id_str)
    prom = db.execute(stmt).scalar_one_or_none()
    if not prom:
        raise ValueError(f"PROM questionnaire '{prom_id_str}' was not found.")

    logger.info("Exporting FHIR Questionnaire resource id=%s", prom.prom_id)
    return FHIRQuestionnaireMapper.to_fhir(prom)


def export_questionnaire_response_as_fhir(
    db: Session, current_user: User, response_id_str: str
) -> FHIRQuestionnaireResponse:
    """Export patient PROM response as standard FHIR R4 QuestionnaireResponse."""
    stmt = select(PROMResponse).where(PROMResponse.response_id == response_id_str)
    resp = db.execute(stmt).scalar_one_or_none()
    if not resp:
        raise ValueError(f"PROM response '{response_id_str}' was not found.")

    logger.info("Exporting FHIR QuestionnaireResponse resource id=%s", resp.response_id)
    return FHIRQuestionnaireResponseMapper.to_fhir(resp)


def export_research_study_as_fhir(
    db: Session, current_user: User, trial_id_str: str
) -> FHIRResearchStudy:
    """Export clinical trial as standard FHIR R4 ResearchStudy resource."""
    from app.services.trial_matching_service import TrialMatchingService
    trial_svc = TrialMatchingService()
    trial_svc.seed_standard_clinical_trials(db)

    trial = trial_svc.get_trial(db, trial_id_str)
    if not trial:
        raise ValueError(f"Clinical trial '{trial_id_str}' was not found.")

    logger.info("Exporting FHIR ResearchStudy resource id=%s", trial.trial_id)
    return FHIRResearchStudyMapper.to_fhir(trial)


def export_biomarker_observation_as_fhir(
    db: Session, current_user: User, observation_id_str: str
) -> FHIRObservation:
    """Export biomarker observation as standard FHIR R4 Observation resource."""
    stmt = (
        select(BiomarkerObservation)
        .options(selectinload(BiomarkerObservation.patient))
        .where(BiomarkerObservation.observation_id == observation_id_str)
    )
    bm = db.execute(stmt).scalar_one_or_none()
    if not bm:
        raise ValueError(f"Biomarker observation '{observation_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and bm.patient and bm.patient.email != current_user.email:
        raise PermissionError("Access denied to requested biomarker observation.")

    logger.info("Exporting FHIR Biomarker Observation resource id=%s", bm.observation_id)
    return FHIRBiomarkerObservationMapper.to_fhir(bm)


def export_genomic_profile_as_fhir(
    db: Session, current_user: User, profile_id_str: str
) -> FHIRDiagnosticReport:
    """Export genomic profile as standard FHIR R4 DiagnosticReport resource."""
    stmt = (
        select(GenomicProfile)
        .options(
            selectinload(GenomicProfile.biomarkers),
            selectinload(GenomicProfile.patient),
        )
        .where(GenomicProfile.profile_id == profile_id_str)
    )
    profile = db.execute(stmt).scalar_one_or_none()
    if not profile:
        raise ValueError(f"Genomic profile '{profile_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and profile.patient and profile.patient.email != current_user.email:
        raise PermissionError("Access denied to requested genomic profile.")

    logger.info("Exporting FHIR Genomic Profile DiagnosticReport resource id=%s", profile.profile_id)
    return FHIRGenomicProfileMapper.to_fhir(profile)


def export_agent_recommendation_task_as_fhir(
    db: Session, current_user: User, recommendation_id_str: str
) -> FHIRTask:
    """Export agent recommendation as standard FHIR R4 Task resource."""
    stmt = (
        select(ClinicalAgentRecommendation)
        .options(selectinload(ClinicalAgentRecommendation.patient))
        .where(ClinicalAgentRecommendation.recommendation_id == recommendation_id_str)
    )
    rec = db.execute(stmt).scalar_one_or_none()
    if not rec:
        raise ValueError(f"Agent recommendation '{recommendation_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and rec.patient and rec.patient.email != current_user.email:
        raise PermissionError("Access denied to requested agent recommendation.")

    patient_id = rec.patient.patient_id if rec.patient else "UNKNOWN"
    logger.info("Exporting FHIR Task resource for agent recommendation id=%s", rec.recommendation_id)
    return FHIRAgentRecommendationTaskMapper.to_fhir(rec, patient_id)


def export_agent_provenance_as_fhir(
    db: Session, current_user: User, run_id_str: str
) -> FHIRProvenance:
    """Export agent execution run as standard FHIR R4 Provenance resource."""
    stmt = (
        select(ClinicalAgentRun)
        .options(
            selectinload(ClinicalAgentRun.patient),
            selectinload(ClinicalAgentRun.recommendations),
        )
        .where(ClinicalAgentRun.run_id == run_id_str)
    )
    run = db.execute(stmt).scalar_one_or_none()
    if not run:
        raise ValueError(f"Agent run '{run_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and run.patient and run.patient.email != current_user.email:
        raise PermissionError("Access denied to requested agent run provenance.")

    patient_id = run.patient.patient_id if run.patient else "UNKNOWN"
    logger.info("Exporting FHIR Provenance resource for agent run id=%s", run.run_id)
    return FHIRAgentProvenanceMapper.to_fhir(run, patient_id)


def export_imaging_study_as_fhir(
    db: Session, current_user: User, study_id_str: str
) -> FHIRImagingStudy:
    """Export ImagingStudy as standard FHIR R4 ImagingStudy resource."""
    stmt = (
        select(ImagingStudy)
        .options(
            selectinload(ImagingStudy.patient),
            selectinload(ImagingStudy.encounter),
            selectinload(ImagingStudy.assets),
            selectinload(ImagingStudy.findings),
            selectinload(ImagingStudy.reports),
        )
        .where((ImagingStudy.study_id == study_id_str) | (ImagingStudy.study_id == f"STU-{study_id_str}"))
    )
    study = db.execute(stmt).scalar_one_or_none()
    if not study:
        # Check if numeric
        if study_id_str.isdigit():
            study = db.get(ImagingStudy, int(study_id_str))
    if not study:
        raise ValueError(f"Imaging study '{study_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and study.patient and study.patient.email != current_user.email:
        raise PermissionError("Access denied to requested imaging study.")

    logger.info("Exporting FHIR ImagingStudy resource id=%s", study.study_id)
    return FHIRImagingStudyMapper.to_fhir(study)


def export_radiology_report_as_fhir(
    db: Session, current_user: User, report_id_str: str
) -> FHIRDiagnosticReport:
    """Export RadiologyReport as standard FHIR R4 DiagnosticReport resource."""
    stmt = (
        select(RadiologyReport)
        .options(
            selectinload(RadiologyReport.patient),
            selectinload(RadiologyReport.study).selectinload(ImagingStudy.findings),
            selectinload(RadiologyReport.encounter),
            selectinload(RadiologyReport.order),
            selectinload(RadiologyReport.author_user),
            selectinload(RadiologyReport.signed_by_user),
        )
        .where((RadiologyReport.report_id == report_id_str) | (RadiologyReport.report_id == f"RAD-{report_id_str}"))
    )
    report = db.execute(stmt).scalar_one_or_none()
    if not report:
        if report_id_str.isdigit():
            report = db.get(RadiologyReport, int(report_id_str))
    if not report:
        raise ValueError(f"Radiology report '{report_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and report.patient and report.patient.email != current_user.email:
        raise PermissionError("Access denied to requested radiology report.")

    logger.info("Exporting FHIR DiagnosticReport resource for radiology report id=%s", report.report_id)
    return FHIRRadiologyReportMapper.to_fhir(report)


def export_imaging_observation_as_fhir(
    db: Session, current_user: User, finding_id_str: str
) -> FHIRObservation:
    """Export ImagingFinding as standard FHIR R4 Observation resource."""
    stmt = (
        select(ImagingFinding)
        .options(
            selectinload(ImagingFinding.patient),
            selectinload(ImagingFinding.study),
            selectinload(ImagingFinding.asset),
        )
        .where((ImagingFinding.finding_id == finding_id_str) | (ImagingFinding.finding_id == f"FND-{finding_id_str}"))
    )
    finding = db.execute(stmt).scalar_one_or_none()
    if not finding:
        if finding_id_str.isdigit():
            finding = db.get(ImagingFinding, int(finding_id_str))
    if not finding:
        raise ValueError(f"Imaging finding '{finding_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and finding.patient and finding.patient.email != current_user.email:
        raise PermissionError("Access denied to requested imaging finding.")

    logger.info("Exporting FHIR Observation resource for imaging finding id=%s", finding.finding_id)
    return FHIRImagingObservationMapper.to_fhir(finding)

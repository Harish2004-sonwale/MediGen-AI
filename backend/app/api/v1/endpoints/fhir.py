from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_smart_scope
from app.database import get_db
from app.models.user import User
from app.schemas.fhir import (
    FHIRBatchImportResponse,
    FHIRBundle,
    FHIRCarePlan,
    FHIRCommunication,
    FHIRComposition,
    FHIRCondition,
    FHIRDevice,
    FHIRDiagnosticReport,
    FHIREncounter,
    FHIRGroup,
    FHIRImagingStudy,
    FHIRImportResult,
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
    FHIRConsent,
    FHIRAuditEvent,
    FHIRCapabilityStatement,
    FHIRCapabilityRest,
    FHIRCapabilityResource,
    FHIRCapabilityInteraction,
)
from app.services.fhir_export_service import (
    export_agent_provenance_as_fhir,
    export_agent_recommendation_task_as_fhir,
    export_biomarker_observation_as_fhir,
    export_care_plan_as_fhir,
    export_care_task_as_fhir,
    export_cohort_as_fhir_group,
    export_condition_as_fhir,
    export_device_as_fhir,
    export_discharge_as_fhir_composition,
    export_encounter_as_fhir,
    export_genomic_profile_as_fhir,
    export_handoff_as_fhir_communication,
    export_imaging_observation_as_fhir,
    export_imaging_study_as_fhir,
    export_medication_statement_as_fhir,
    export_observation_as_fhir,
    export_order_as_fhir_service_request,
    export_patient_as_fhir,
    export_patient_bundle_as_fhir,
    export_quality_measure_as_fhir,
    export_quality_report_as_fhir,
    export_questionnaire_as_fhir,
    export_questionnaire_response_as_fhir,
    export_radiology_report_as_fhir,
    export_research_study_as_fhir,
    export_result_as_fhir_diagnostic_report,
    export_risk_assessment_as_fhir,
    export_audit_event_as_fhir,
    export_consent_as_fhir,
    export_patient_consents_bundle_as_fhir,
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
    dependencies=[Depends(require_smart_scope("patient/Patient.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/Encounter.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/Condition.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/MedicationStatement.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/Observation.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/Patient.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/CarePlan.read"))],
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
    dependencies=[Depends(require_smart_scope("patient/Task.read"))],
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


@router.get(
    "/ServiceRequest/{order_id}",
    response_model=FHIRServiceRequest,
    status_code=status.HTTP_200_OK,
    summary="Export clinical order as a FHIR R4 ServiceRequest resource",
)
def get_fhir_service_request(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRServiceRequest:
    """Retrieve and export a clinical diagnostic/laboratory order as a standard FHIR R4 ServiceRequest resource."""
    try:
        return export_order_as_fhir_service_request(db, current_user, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/DiagnosticReport/{result_id}",
    response_model=FHIRDiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Export diagnostic result as a FHIR R4 DiagnosticReport resource",
    dependencies=[Depends(require_smart_scope("patient/DiagnosticReport.read"))],
)
def get_fhir_diagnostic_report(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRDiagnosticReport:
    """Retrieve and export a diagnostic result report as a standard FHIR R4 DiagnosticReport resource."""
    try:
        return export_result_as_fhir_diagnostic_report(db, current_user, result_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Measure/{measure_id}",
    response_model=FHIRMeasure,
    status_code=status.HTTP_200_OK,
    summary="Export a Clinical Quality Measure as a standard FHIR R4 Measure",
)
def get_fhir_measure(
    measure_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRMeasure:
    """Retrieve and export a clinical quality measure definition as FHIR R4 Measure."""
    try:
        return export_quality_measure_as_fhir(db, current_user, measure_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/MeasureReport/{report_id}",
    response_model=FHIRMeasureReport,
    status_code=status.HTTP_200_OK,
    summary="Export a population compliance audit report as a standard FHIR R4 MeasureReport",
)
def get_fhir_measure_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRMeasureReport:
    """Retrieve and export a population compliance report as FHIR R4 MeasureReport."""
    try:
        return export_quality_report_as_fhir(db, current_user, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/Device/{device_id}",

    response_model=FHIRDevice,
    status_code=status.HTTP_200_OK,
    summary="Export a registered RPM device as a standard FHIR R4 Device resource",
)
def get_fhir_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRDevice:
    """Retrieve and export a registered RPM device as FHIR R4 Device."""
    try:
        return export_device_as_fhir(db, current_user, device_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Questionnaire/{prom_id}",
    response_model=FHIRQuestionnaire,
    status_code=status.HTTP_200_OK,
    summary="Export a standardized PROM survey as a standard FHIR R4 Questionnaire",
)
def get_fhir_questionnaire(
    prom_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRQuestionnaire:
    """Retrieve and export a PROM definition as FHIR R4 Questionnaire."""
    try:
        return export_questionnaire_as_fhir(db, current_user, prom_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/QuestionnaireResponse/{response_id}",
    response_model=FHIRQuestionnaireResponse,
    status_code=status.HTTP_200_OK,
    summary="Export a patient PROM submission as a standard FHIR R4 QuestionnaireResponse",
)
def get_fhir_questionnaire_response(
    response_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRQuestionnaireResponse:
    """Retrieve and export a PROM submission as FHIR R4 QuestionnaireResponse."""
    try:
        return export_questionnaire_response_as_fhir(db, current_user, response_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/ResearchStudy/{trial_id}",
    response_model=FHIRResearchStudy,
    status_code=status.HTTP_200_OK,
    summary="Export a clinical trial as a standard FHIR R4 ResearchStudy",
)
def get_fhir_research_study(
    trial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRResearchStudy:
    """Retrieve and export a clinical trial as FHIR R4 ResearchStudy."""
    try:
        return export_research_study_as_fhir(db, current_user, trial_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Biomarker/{observation_id}",
    response_model=FHIRObservation,
    status_code=status.HTTP_200_OK,
    summary="Export a genomic biomarker observation as a standard FHIR R4 Observation",
)
def get_fhir_biomarker_observation(
    observation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRObservation:
    """Retrieve and export a genomic biomarker observation as FHIR R4 Observation."""
    try:
        return export_biomarker_observation_as_fhir(db, current_user, observation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/GenomicProfile/{profile_id}",
    response_model=FHIRDiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Export a patient genomic profile panel as a standard FHIR R4 DiagnosticReport",
)
def get_fhir_genomic_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRDiagnosticReport:
    """Retrieve and export a patient genomic profile panel as FHIR R4 DiagnosticReport."""
    try:
        return export_genomic_profile_as_fhir(db, current_user, profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Provenance/{run_id}",
    response_model=FHIRProvenance,
    status_code=status.HTTP_200_OK,
    summary="Export Clinical AI Agent Run as FHIR R4 Provenance",
)
def get_fhir_agent_provenance(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRProvenance:
    """Retrieve and export a clinical AI agent run as standard FHIR R4 Provenance with cryptographic SHA-256 signatures."""
    try:
        return export_agent_provenance_as_fhir(db, current_user, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/AgentTask/{recommendation_id}",
    response_model=FHIRTask,
    status_code=status.HTTP_200_OK,
    summary="Export Clinical AI Agent Recommendation as FHIR R4 Task",
)
def get_fhir_agent_recommendation_task(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRTask:
    """Retrieve and export a clinical agent care recommendation as standard FHIR R4 Task proposal."""
    try:
        return export_agent_recommendation_task_as_fhir(db, current_user, recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/ImagingStudy/{study_id}",
    response_model=FHIRImagingStudy,
    status_code=status.HTTP_200_OK,
    summary="Export Medical Imaging Study as FHIR R4 ImagingStudy",
)
def get_fhir_imaging_study(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRImagingStudy:
    """Retrieve and export a medical imaging study as standard FHIR R4 ImagingStudy resource."""
    try:
        return export_imaging_study_as_fhir(db, current_user, study_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/ImagingReport/{report_id}",
    response_model=FHIRDiagnosticReport,
    status_code=status.HTTP_200_OK,
    summary="Export Radiology Diagnostic Report as FHIR R4 DiagnosticReport",
)
def get_fhir_radiology_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRDiagnosticReport:
    """Retrieve and export a radiology report as standard FHIR R4 DiagnosticReport resource."""
    try:
        return export_radiology_report_as_fhir(db, current_user, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/ImagingObservation/{finding_id}",
    response_model=FHIRObservation,
    status_code=status.HTTP_200_OK,
    summary="Export Structured Imaging Finding as FHIR R4 Observation",
)
def get_fhir_imaging_observation(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRObservation:
    """Retrieve and export a structured imaging finding as standard FHIR R4 Observation resource."""
    try:
        return export_imaging_observation_as_fhir(db, current_user, finding_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/Consent/{consent_id}",
    response_model=FHIRConsent,
    status_code=status.HTTP_200_OK,
    summary="Export patient consent directive as FHIR R4 Consent resource",
)
def get_fhir_consent(
    consent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRConsent:
    """Retrieve and export patient consent directive as standard FHIR R4 Consent resource."""
    try:
        return export_consent_as_fhir(db, current_user, consent_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/AuditEvent/{event_id}",
    response_model=FHIRAuditEvent,
    status_code=status.HTTP_200_OK,
    summary="Export clinical audit record as FHIR R4 AuditEvent resource",
)
def get_fhir_audit_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRAuditEvent:
    """Retrieve and export clinical audit event as standard FHIR R4 AuditEvent resource."""
    try:
        return export_audit_event_as_fhir(db, current_user, event_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/consents",
    response_model=FHIRBundle,
    status_code=status.HTTP_200_OK,
    summary="Export patient consent directives as FHIR R4 collection Bundle",
)
def get_fhir_patient_consents_bundle(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRBundle:
    """Retrieve and export all consent directives for a patient as a FHIR R4 collection Bundle."""
    try:
        return export_patient_consents_bundle_as_fhir(db, current_user, patient_id)
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


@router.get(
    "/metadata",
    response_model=FHIRCapabilityStatement,
    status_code=status.HTTP_200_OK,
    summary="Get FHIR R4 CapabilityStatement for MediGen AI platform",
)
def get_fhir_capability_statement() -> FHIRCapabilityStatement:
    """Return FHIR R4 CapabilityStatement declaring server conformance, resources, and interactions."""
    resource_types = [
        ("Patient", ["read", "search-type"]),
        ("Encounter", ["read"]),
        ("Condition", ["read"]),
        ("MedicationStatement", ["read"]),
        ("Observation", ["read"]),
        ("DiagnosticReport", ["read"]),
        ("CarePlan", ["read"]),
        ("ServiceRequest", ["read"]),
        ("Group", ["read"]),
        ("Communication", ["read"]),
        ("Composition", ["read"]),
        ("Measure", ["read"]),
        ("MeasureReport", ["read"]),
        ("Device", ["read"]),
        ("Questionnaire", ["read"]),
        ("QuestionnaireResponse", ["read"]),
        ("ResearchStudy", ["read"]),
        ("RiskAssessment", ["read"]),
        ("ImagingStudy", ["read"]),
        ("Consent", ["read"]),
        ("AuditEvent", ["read"]),
    ]

    resources = [
        FHIRCapabilityResource(
            type=rtype,
            profile=f"http://hl7.org/fhir/StructureDefinition/{rtype}",
            interaction=[FHIRCapabilityInteraction(code=code) for code in ops],
        )
        for rtype, ops in resource_types
    ]

    return FHIRCapabilityStatement(
        id="medigen-ai-capability-statement",
        status="active",
        date="2026-08-30T00:00:00Z",
        publisher="MediGen AI Clinical Intelligence Platform",
        kind="instance",
        software={
            "name": "MediGen AI Clinical Platform",
            "version": "0.1.0",
        },
        implementation={
            "description": "MediGen AI FHIR R4 Interoperability Gateway & Clinical Decision Support System",
            "url": "http://localhost:8000/api/v1/fhir",
        },
        fhirVersion="4.0.1",
        format=["application/fhir+json", "application/json"],
        rest=[
            FHIRCapabilityRest(
                mode="server",
                documentation="RESTful FHIR R4 Clinical Decision Support & Interoperability Gateway",
                security={
                    "cors": True,
                    "service": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/restful-security-service",
                                    "code": "OAuth",
                                    "display": "OAuth2 / JWT Bearer Authentication",
                                }
                            ]
                        }
                    ],
                },
                resource=resources,
            )
        ],
    )

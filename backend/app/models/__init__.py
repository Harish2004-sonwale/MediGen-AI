"""Models package exposing ORM entities."""

from app.models.alert import ClinicalAlert
from app.models.appointment import Appointment
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.chat import ChatMessage, ChatSession
from app.models.cohort import CohortMembership, PatientCohort
from app.models.discharge import DischargeProtocol
from app.models.doctor import Doctor
from app.models.document import DocumentChunk, MedicalDocument
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.media import DiagnosticMedia
from app.models.note import ClinicalNote
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.quality import (
    QualityMeasure,
    QualityMeasureGap,
    QualityMeasureReport,
    QualityMeasureResult,
)
from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.user import User
from app.models.vital import VitalTelemetry

from app.models.rpm import (
    PROMDefinition,
    PROMResponse,
    RPMDevice,
    RPMEscalationAlert,
    RPMObservation,
    RPMProgram,
    RPMThresholdRule,
    TelehealthSession,
)
from app.models.trials import (
    BiomarkerObservation,
    ClinicalTrial,
    GenomicProfile,
    PrecisionTreatmentEligibility,
    TrialEligibilityCriterion,
    TrialMatch,
)
from app.models.agents import (
    AgentEvidenceReference,
    ClinicalAgentDefinition,
    ClinicalAgentRecommendation,
    ClinicalAgentRun,
)
from app.models.imaging import (
    ImagingAsset,
    ImagingFinding,
    ImagingStudy,
    RadiologyReport,
)
from app.models.security import (
    ClinicalAuditEvent,
    DataRetentionPolicy,
    LegalClinicalHold,
    PatientConsent,
    SecurityIncident,
)
from app.models.tenant import (
    ClinicalFacility,
    DepartmentUnit,
    EHRIntegrationConfig,
    HealthOrganization,
    SmartAuthSession,
    TerminologyMapping,
)
from app.models.outbox import OutboxEvent
from app.models.idempotency import IdempotencyRecord
from app.models.mfa import MFACredential
from app.models.fhir_subscription import FHIRSubscription
from app.models.bulk_export import BulkExportJob
from app.models.empi import (
    EMPIMatchReview,
    EMPIMergeHistory,
    EnterprisePatientIdentity,
    PatientIdentityLink,
)
from app.models.ccda import CCDADocumentExchange
from app.models.pathway import (
    PatientPathwayEnrollment,
    PatientPathwayStageEvent,
    PathwayMilestone,
    PathwayStage,
    RegionalClinicalPathway,
)

__all__ = [
    "User",
    "Patient",
    "Encounter",
    "Doctor",
    "Appointment",
    "MedicalDocument",
    "DocumentChunk",
    "ChatSession",
    "ChatMessage",
    "DiagnosticMedia",
    "ClinicalNote",
    "VitalTelemetry",
    "ClinicalAlert",
    "CarePlan",
    "CareTask",
    "PatientCohort",
    "CohortMembership",
    "ClinicalRiskAssessment",
    "ClinicalHandoff",
    "DischargeProtocol",
    "ClinicalOrder",
    "DiagnosticResult",
    "QualityMeasure",
    "QualityMeasureResult",
    "QualityMeasureGap",
    "QualityMeasureReport",
    "RPMProgram",
    "RPMDevice",
    "RPMObservation",
    "RPMThresholdRule",
    "RPMEscalationAlert",
    "PROMDefinition",
    "PROMResponse",
    "TelehealthSession",
    "ClinicalTrial",
    "TrialEligibilityCriterion",
    "GenomicProfile",
    "BiomarkerObservation",
    "TrialMatch",
    "PrecisionTreatmentEligibility",
    "ClinicalAgentDefinition",
    "ClinicalAgentRun",
    "ClinicalAgentRecommendation",
    "AgentEvidenceReference",
    "ImagingStudy",
    "ImagingAsset",
    "ImagingFinding",
    "RadiologyReport",
    "ClinicalAuditEvent",
    "PatientConsent",
    "SecurityIncident",
    "DataRetentionPolicy",
    "LegalClinicalHold",
    "HealthOrganization",
    "ClinicalFacility",
    "DepartmentUnit",
    "EHRIntegrationConfig",
    "SmartAuthSession",
    "TerminologyMapping",
    "OutboxEvent",
    "IdempotencyRecord",
    "MFACredential",
    "FHIRSubscription",
    "BulkExportJob",
    "EnterprisePatientIdentity",
    "PatientIdentityLink",
    "EMPIMatchReview",
    "EMPIMergeHistory",
    "CCDADocumentExchange",
    "RegionalClinicalPathway",
    "PathwayStage",
    "PathwayMilestone",
    "PatientPathwayEnrollment",
    "PatientPathwayStageEvent",
]


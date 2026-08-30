from datetime import date, datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class FHIRResourceType(str, Enum):
    PATIENT = "Patient"
    ENCOUNTER = "Encounter"
    CONDITION = "Condition"
    MEDICATION_STATEMENT = "MedicationStatement"
    OBSERVATION = "Observation"
    CARE_PLAN = "CarePlan"
    GOAL = "Goal"
    TASK = "Task"
    GROUP = "Group"
    RISK_ASSESSMENT = "RiskAssessment"
    COMPOSITION = "Composition"
    COMMUNICATION = "Communication"
    SERVICE_REQUEST = "ServiceRequest"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    MEASURE = "Measure"
    MEASURE_REPORT = "MeasureReport"
    DEVICE = "Device"
    QUESTIONNAIRE = "Questionnaire"
    QUESTIONNAIRE_RESPONSE = "QuestionnaireResponse"
    RESEARCH_STUDY = "ResearchStudy"
    PROVENANCE = "Provenance"
    IMAGING_STUDY = "ImagingStudy"
    CONSENT = "Consent"
    AUDIT_EVENT = "AuditEvent"
    BUNDLE = "Bundle"











class FHIRCoding(BaseModel):
    system: Optional[str] = Field(default=None, description="Identity of the terminology system")
    version: Optional[str] = Field(default=None, description="Version of the system")
    code: Optional[str] = Field(default=None, description="Symbol in syntax defined by the system")
    display: Optional[str] = Field(default=None, description="Representation defined by the system")
    userSelected: Optional[bool] = Field(default=None, description="If this coding was chosen directly by the user")


class FHIRCodeableConcept(BaseModel):
    coding: list[FHIRCoding] = Field(default_factory=list, description="Code defined by a terminology system")
    text: Optional[str] = Field(default=None, description="Plain text representation")


class FHIRIdentifier(BaseModel):
    use: Optional[str] = Field(default=None, description="usual | official | temp | secondary | old")
    system: Optional[str] = Field(default=None, description="The namespace for the identifier value")
    value: Optional[str] = Field(default=None, description="The value that is unique")


class FHIRReference(BaseModel):
    reference: Optional[str] = Field(default=None, description="Literal reference, Relative, internal or absolute URL")
    type: Optional[str] = Field(default=None, description="Type the reference refers to (e.g. Patient)")
    identifier: Optional[FHIRIdentifier] = Field(default=None, description="Logical reference, when literal reference is not known")
    display: Optional[str] = Field(default=None, description="Text alternative for the resource")


class FHIRPeriod(BaseModel):
    start: Optional[str] = Field(default=None, description="Starting time with inclusive boundary")
    end: Optional[str] = Field(default=None, description="End time with inclusive boundary")


class FHIRHumanName(BaseModel):
    use: Optional[str] = Field(default="official", description="usual | official | temp | nickname | anonymous | old | maiden")
    text: Optional[str] = Field(default=None, description="Text representation of the full name")
    family: Optional[str] = Field(default=None, description="Family name (often called 'Surname')")
    given: list[str] = Field(default_factory=list, description="Given names (not always 'first'). Includes middle names")
    prefix: list[str] = Field(default_factory=list, description="Parts that come before the name")
    suffix: list[str] = Field(default_factory=list, description="Parts that come after the name")


class FHIRContactPoint(BaseModel):
    system: Optional[str] = Field(default=None, description="phone | fax | email | pager | url | sms | other")
    value: Optional[str] = Field(default=None, description="The actual contact point details")
    use: Optional[str] = Field(default="home", description="home | work | temp | old | mobile")


class FHIRAddress(BaseModel):
    use: Optional[str] = Field(default="home", description="home | work | temp | old | billing")
    type: Optional[str] = Field(default="both", description="postal | physical | both")
    text: Optional[str] = Field(default=None, description="Text representation of the address")
    line: list[str] = Field(default_factory=list, description="Street name, number, direction & P.O. Box etc.")
    city: Optional[str] = Field(default=None, description="Name of city, town etc.")
    state: Optional[str] = Field(default=None, description="Sub-unit of country (abbreviations ok)")
    postalCode: Optional[str] = Field(default=None, description="Postal code for area")
    country: Optional[str] = Field(default=None, description="Country (can be ISO 3166 2 or 3 letter code)")


class FHIRPatientContact(BaseModel):
    relationship: list[FHIRCodeableConcept] = Field(default_factory=list, description="The kind of relationship")
    name: Optional[FHIRHumanName] = Field(default=None, description="A name associated with the contact person")
    telecom: list[FHIRContactPoint] = Field(default_factory=list, description="Contact details for the person")


class FHIRQuantity(BaseModel):
    value: Optional[float] = Field(default=None, description="Numerical value")
    unit: Optional[str] = Field(default=None, description="Unit representation")
    system: Optional[str] = Field(default="http://unitsofmeasure.org", description="System that defines coded unit form")
    code: Optional[str] = Field(default=None, description="Coded form of the unit")


class FHIRDosage(BaseModel):
    text: Optional[str] = Field(default=None, description="Free text dosage instructions")
    patientInstruction: Optional[str] = Field(default=None, description="Patient oriented instructions")


# Concrete FHIR R4 Resources

class FHIRPatient(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Patient", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="An identifier for this patient")
    active: Optional[bool] = Field(default=True, description="Whether this patient's record is in active use")
    name: list[FHIRHumanName] = Field(default_factory=list, description="A name associated with the patient")
    telecom: list[FHIRContactPoint] = Field(default_factory=list, description="A contact detail for the individual")
    gender: Optional[str] = Field(default=None, description="male | female | other | unknown")
    birthDate: Optional[str] = Field(default=None, description="The date of birth for the individual (YYYY-MM-DD)")
    address: list[FHIRAddress] = Field(default_factory=list, description="An address for the individual")
    contact: list[FHIRPatientContact] = Field(default_factory=list, description="A contact party (e.g. guardian, partner, friend)")


class FHIREncounterDiagnosis(BaseModel):
    condition: FHIRReference = Field(..., description="The condition or diagnosis")
    use: Optional[FHIRCodeableConcept] = Field(default=None, description="Role that this diagnosis has within the encounter")
    rank: Optional[int] = Field(default=None, description="Ranking of the diagnosis (for billing etc.)")


class FHIREncounter(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Encounter", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Identifier(s) by which this encounter is known")
    status: str = Field(default="finished", description="planned | arrived | triaged | in-progress | onleave | finished | cancelled +")
    class_: Optional[FHIRCoding] = Field(default=None, alias="class", description="Classification of patient encounter")
    type: list[FHIRCodeableConcept] = Field(default_factory=list, description="Specific type of encounter")
    subject: Optional[FHIRReference] = Field(default=None, description="The patient or group present at the encounter")
    period: Optional[FHIRPeriod] = Field(default=None, description="The start and end-time of the encounter")
    reasonCode: list[FHIRCodeableConcept] = Field(default_factory=list, description="Coded reason the encounter takes place")
    diagnosis: list[FHIREncounterDiagnosis] = Field(default_factory=list, description="The list of diagnosis relevant to this encounter")


class FHIRAnnotation(BaseModel):
    text: str = Field(..., description="The annotation text")
    time: Optional[str] = Field(default=None, description="When the annotation was made")


class FHIRCondition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Condition", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="External Ids for this condition")
    clinicalStatus: Optional[FHIRCodeableConcept] = Field(default=None, description="active | recurrence | relapse | inactive | remission | resolved")
    verificationStatus: Optional[FHIRCodeableConcept] = Field(default=None, description="unconfirmed | provisional | differential | confirmed | refuted | entered-in-error")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="problem-list-item | encounter-diagnosis")
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="Identification of the condition, problem or diagnosis")
    subject: FHIRReference = Field(..., description="Who has the condition?")
    encounter: Optional[FHIRReference] = Field(default=None, description="Encounter created as part of")
    recordedDate: Optional[str] = Field(default=None, description="Date record was first recorded")
    note: list[FHIRAnnotation] = Field(default_factory=list, description="Additional information about the Condition")


class FHIRMedicationStatement(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="MedicationStatement", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="External identifier")
    status: str = Field(default="active", description="active | completed | entered-in-error | intended | stopped | on-hold | unknown | not-taken")
    medicationCodeableConcept: Optional[FHIRCodeableConcept] = Field(default=None, description="What medication was taken")
    subject: FHIRReference = Field(..., description="Who is/was taking the medication")
    effectiveDateTime: Optional[str] = Field(default=None, description="The date/time or interval when the medication is/was taken")
    dateAsserted: Optional[str] = Field(default=None, description="When the statement was asserted")
    dosage: list[FHIRDosage] = Field(default_factory=list, description="Details of how medication was taken")
    note: list[FHIRAnnotation] = Field(default_factory=list, description="Further information about the statement")


class FHIRObservation(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Observation", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Business Identifier for observation")
    status: str = Field(default="final", description="registered | preliminary | final | amended +")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Classification of type of observation")
    code: FHIRCodeableConcept = Field(..., description="Type of observation (code / type)")
    subject: Optional[FHIRReference] = Field(default=None, description="Who and/or what the observation is about")
    effectiveDateTime: Optional[str] = Field(default=None, description="Clinically relevant time/time-period for observation")
    valueQuantity: Optional[FHIRQuantity] = Field(default=None, description="Actual result if quantitative")
    valueString: Optional[str] = Field(default=None, description="Actual result if string")
    note: list[FHIRAnnotation] = Field(default_factory=list, description="Comments about the observation")


# FHIR Goal Resource Schema

class FHIRGoal(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Goal", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="External Ids for this goal")
    lifecycleStatus: str = Field(default="active", description="proposed | planned | accepted | active | on-hold | completed | cancelled")
    description: FHIRCodeableConcept = Field(..., description="Code or text describing goal")
    subject: Optional[FHIRReference] = Field(default=None, description="Who this goal is intended for")
    targetDate: Optional[str] = Field(default=None, description="Target completion date")


# FHIR Task Resource Schema

class FHIRTask(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Task", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Task Instance Identifier")
    status: str = Field(default="requested", description="draft | requested | received | accepted | rejected | ready | cancelled | in-progress | on-hold | failed | completed | entered-in-error")
    intent: str = Field(default="order", description="proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option")
    priority: Optional[str] = Field(default="routine", description="routine | urgent | asap | stat")
    description: Optional[str] = Field(default=None, description="Human-readable explanation of task")
    focus: Optional[FHIRReference] = Field(default=None, description="What task is acting on")
    for_reference: Optional[FHIRReference] = Field(default=None, alias="for", description="Beneficiary of the Task")
    executionPeriod: Optional[FHIRPeriod] = Field(default=None, description="Start and end time of execution")
    authoredOn: Optional[str] = Field(default=None, description="Task Creation Date")


# FHIR CarePlan Resource Schema

class FHIRCarePlanActivityDetail(BaseModel):
    kind: Optional[str] = Field(default="ServiceRequest", description="Kind of resource")
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="Detail type of activity")
    status: str = Field(default="not-started", description="not-started | scheduled | in-progress | on-hold | completed | cancelled | stopped | unknown | entered-in-error")
    description: Optional[str] = Field(default=None, description="Extra info on activity")


class FHIRCarePlanActivity(BaseModel):
    detail: Optional[FHIRCarePlanActivityDetail] = Field(default=None, description="In-line definition of activity")


class FHIRCarePlan(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="CarePlan", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="External Ids for this plan")
    status: str = Field(default="draft", description="draft | active | on-hold | revoked | completed | entered-in-error | unknown")
    intent: str = Field(default="plan", description="proposal | plan | order | option")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Type of plan")
    title: Optional[str] = Field(default=None, description="Human-friendly name for the care plan")
    description: Optional[str] = Field(default=None, description="Summary of nature of plan")
    subject: Optional[FHIRReference] = Field(default=None, description="Who the care plan is for")
    period: Optional[FHIRPeriod] = Field(default=None, description="Time period plan covers")
    goal: list[FHIRReference] = Field(default_factory=list, description="Desired outcome of plan")
    activity: list[FHIRCarePlanActivity] = Field(default_factory=list, description="Action to occur as part of plan")


class FHIRGroupMember(BaseModel):
    entity: FHIRReference = Field(..., description="Reference to patient member")
    inactive: Optional[bool] = Field(default=False, description="Whether member is no longer in group")


class FHIRGroup(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Group", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Unique id")
    active: bool = Field(default=True, description="Whether this group's record is in active use")
    type: str = Field(default="person", description="person | animal | practitioner | device | medication | substance")
    actual: bool = Field(default=True, description="Descriptive or actual")
    name: Optional[str] = Field(default=None, description="Label for Group")
    quantity: Optional[int] = Field(default=None, description="Number of members")
    member: list[FHIRGroupMember] = Field(default_factory=list, description="Who or what is in group")


class FHIRRiskAssessmentPrediction(BaseModel):
    outcome: Optional[FHIRCodeableConcept] = Field(default=None, description="Possible outcome for the subject")
    probabilityDecimal: Optional[float] = Field(default=None, description="Likelihood of specified outcome (0-100 or 0-1)")
    qualitativeRisk: Optional[FHIRCodeableConcept] = Field(default=None, description="Likelihood of specified outcome as a concept (LOW, MODERATE, HIGH, CRITICAL)")
    rationale: Optional[str] = Field(default=None, description="Explanation of prediction")


class FHIRRiskAssessment(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="RiskAssessment", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Unique id")
    status: str = Field(default="final", description="registered | preliminary | final | amended +")
    subject: Optional[FHIRReference] = Field(default=None, description="Who/what does assessment apply to?")
    encounter: Optional[FHIRReference] = Field(default=None, description="Where was assessment performed?")
    occurrenceDateTime: Optional[str] = Field(default=None, description="When was assessment made?")
    prediction: list[FHIRRiskAssessmentPrediction] = Field(default_factory=list, description="Outcome predicted")
    mitigation: Optional[str] = Field(default=None, description="How to reduce risk")


class FHIRCompositionSection(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = Field(default=None, description="Label for section (e.g. for TOC)")
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="Classification of section (recommended)")
    text: Optional[dict[str, Any]] = Field(default=None, description="Text summary of the section, for human interpretation")


class FHIRComposition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Composition", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Version-independent identifier")
    status: str = Field(default="final", description="preliminary | final | amended | entered-in-error")
    type: FHIRCodeableConcept = Field(..., description="Kind of composition (e.g. LOINC 18842-5 Discharge Summary)")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Categorization of Composition")
    subject: Optional[FHIRReference] = Field(default=None, description="Who and/or what the composition is about")
    encounter: Optional[FHIRReference] = Field(default=None, description="Context of the Composition")
    date: Optional[str] = Field(default=None, description="Composition editing time")
    author: list[FHIRReference] = Field(default_factory=list, description="Who and/or what authored the composition")
    title: str = Field(..., description="Human Readable name/title")
    section: list[FHIRCompositionSection] = Field(default_factory=list, description="Composition is broken into sections")


class FHIRCommunication(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Communication", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Unique identifier")
    status: str = Field(default="completed", description="preparation | in-progress | on-hold | stopped | completed | entered-in-error | unknown")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Message category (e.g. clinical-handoff)")
    priority: Optional[str] = Field(default="routine", description="routine | urgent | asap | stat")
    subject: Optional[FHIRReference] = Field(default=None, description="Focus of message (e.g. Patient)")
    encounter: Optional[FHIRReference] = Field(default=None, description="Encounter associated with communication")
    sent: Optional[str] = Field(default=None, description="When sent")
    received: Optional[str] = Field(default=None, description="When received")
    sender: Optional[FHIRReference] = Field(default=None, description="Message sender")
    recipient: list[FHIRReference] = Field(default_factory=list, description="Message recipient")
    payload: list[dict[str, Any]] = Field(default_factory=list, description="Message payload content")


class FHIRServiceRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="ServiceRequest", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Identifiers assigned to this order")
    status: str = Field(default="active", description="draft | active | on-hold | revoked | completed | entered-in-error | unknown")
    intent: str = Field(default="order", description="proposal | plan | directive | order | original-order | reflex-order | filler-order | instance-order | option")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Classification of service")
    priority: Optional[str] = Field(default="routine", description="routine | urgent | asap | stat")
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="What is being requested/ordered")
    subject: FHIRReference = Field(..., description="Individual the service is ordered for")
    encounter: Optional[FHIRReference] = Field(default=None, description="Encounter in which the request was created")
    occurrenceDateTime: Optional[str] = Field(default=None, description="When service should occur")
    authoredOn: Optional[str] = Field(default=None, description="Date request signed")
    requester: Optional[FHIRReference] = Field(default=None, description="Who/what is requesting service")
    reasonCode: list[FHIRCodeableConcept] = Field(default_factory=list, description="Explanation/Justification for procedure or service")


class FHIRDiagnosticReport(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="DiagnosticReport", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Business identifier for report")
    basedOn: list[FHIRReference] = Field(default_factory=list, description="What was requested (ServiceRequest reference)")
    status: str = Field(default="final", description="registered | partial | preliminary | final | amended | corrected | appended | cancelled | entered-in-error | unknown")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Service category (e.g. LAB, RAD)")
    code: FHIRCodeableConcept = Field(..., description="Name/Code for this diagnostic report (LOINC)")
    subject: Optional[FHIRReference] = Field(default=None, description="The subject of the report")
    encounter: Optional[FHIRReference] = Field(default=None, description="Health care event when test was ordered")
    effectiveDateTime: Optional[str] = Field(default=None, description="Clinically relevant time/time-period for report")
    issued: Optional[str] = Field(default=None, description="DateTime this version was made")
    performer: list[FHIRReference] = Field(default_factory=list, description="Responsible Diagnostic Service")
    result: list[FHIRReference] = Field(default_factory=list, description="Observations forming part of this report")
    conclusion: Optional[str] = Field(default=None, description="Clinical conclusion (interpretation) of test results")


class FHIRMeasure(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Measure", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    url: Optional[str] = Field(default=None, description="Canonical identifier for this measure")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Additional identifier for the measure")
    version: Optional[str] = Field(default="1.0.0", description="Business version of the measure")
    name: Optional[str] = Field(default=None, description="Name for this measure (computer friendly)")
    title: Optional[str] = Field(default=None, description="Name for this measure (human friendly)")
    status: str = Field(default="active", description="draft | active | retired | unknown")
    description: Optional[str] = Field(default=None, description="Natural language description of the measure")
    topic: list[FHIRCodeableConcept] = Field(default_factory=list, description="The category of the measure (e.g. chronic_disease_management)")


class FHIRMeasureReportGroupStratifier(BaseModel):
    code: list[FHIRCodeableConcept] = Field(default_factory=list)
    stratum: list[dict[str, Any]] = Field(default_factory=list)


class FHIRMeasureReportGroupPopulation(BaseModel):
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="initial-population | numerator | denominator | denominator-exclusion | denominator-exception")
    count: Optional[int] = Field(default=0, description="Size of the population")


class FHIRMeasureReportGroup(BaseModel):
    code: Optional[FHIRCodeableConcept] = Field(default=None, description="Meaning of the group")
    population: list[FHIRMeasureReportGroupPopulation] = Field(default_factory=list, description="The populations in the group")
    measureScore: Optional[FHIRQuantity] = Field(default=None, description="What score this group achieved")


class FHIRMeasureReport(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="MeasureReport", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Additional identifier for the measure report")
    status: str = Field(default="complete", description="complete | pending | error")
    type: str = Field(default="summary", description="individual | subject-list | summary | data-exchange")
    measure: str = Field(..., description="What measure was calculated (canonical URL or reference)")
    subject: Optional[FHIRReference] = Field(default=None, description="What individual(s) the report is for")
    date: Optional[str] = Field(default=None, description="When the report was generated")
    reporter: Optional[FHIRReference] = Field(default=None, description="Who is reporting the data")
    period: FHIRPeriod = Field(..., description="What period the report covers")
    group: list[FHIRMeasureReportGroup] = Field(default_factory=list, description="Measure results for each group")
    evaluatedResource: list[FHIRReference] = Field(default_factory=list, description="What data was used to calculate the measure score")






class FHIRDevice(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Device", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Instance identifier")
    status: str = Field(default="active", description="active | inactive | entered-in-error | unknown")
    manufacturer: Optional[str] = Field(default=None, description="Name of device manufacturer")
    modelNumber: Optional[str] = Field(default=None, description="The manufacturer's model number for the device")
    serialNumber: Optional[str] = Field(default=None, description="Serial number assigned by the manufacturer")
    type: Optional[FHIRCodeableConcept] = Field(default=None, description="The kind or type of device")
    patient: Optional[FHIRReference] = Field(default=None, description="Patient to whom Device is affiliated")


class FHIRQuestionnaireItemOption(BaseModel):
    valueCoding: Optional[FHIRCoding] = None
    valueString: Optional[str] = None
    valueInteger: Optional[int] = None


class FHIRQuestionnaireItem(BaseModel):
    linkId: str = Field(..., description="Unique id for item in questionnaire")
    text: Optional[str] = Field(default=None, description="Primary text for the item")
    type: str = Field(default="choice", description="group | display | boolean | decimal | integer | date | dateTime | time | string | text | url | choice | open-choice | attachment | reference | quantity")
    required: Optional[bool] = Field(default=False, description="Whether the item must be included in response")
    answerOption: list[FHIRQuestionnaireItemOption] = Field(default_factory=list, description="Permitted answer options")


class FHIRQuestionnaire(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Questionnaire", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="External identifier for questionnaire")
    url: Optional[str] = Field(default=None, description="Canonical identifier for this questionnaire")
    version: Optional[str] = Field(default="1.0.0", description="Business version of the questionnaire")
    title: Optional[str] = Field(default=None, description="Name for this questionnaire (human friendly)")
    status: str = Field(default="active", description="draft | active | retired | unknown")
    date: Optional[str] = Field(default=None, description="Date last changed")
    publisher: Optional[str] = Field(default="MediGen-AI", description="Name of the publisher/steward")
    description: Optional[str] = Field(default=None, description="Natural language description of the questionnaire")
    item: list[FHIRQuestionnaireItem] = Field(default_factory=list, description="Questions and sections within the Questionnaire")


class FHIRQuestionnaireResponseItemAnswer(BaseModel):
    valueDecimal: Optional[float] = None
    valueInteger: Optional[int] = None
    valueString: Optional[str] = None
    valueCoding: Optional[FHIRCoding] = None


class FHIRQuestionnaireResponseItem(BaseModel):
    linkId: str = Field(..., description="Pointer to specific item from Questionnaire")
    text: Optional[str] = Field(default=None, description="Name for group or question text")
    answer: list[FHIRQuestionnaireResponseItemAnswer] = Field(default_factory=list, description="The response(s) to the question")


class FHIRQuestionnaireResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="QuestionnaireResponse", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: Optional[FHIRIdentifier] = Field(default=None, description="Unique id for this set of answers")
    questionnaire: Optional[str] = Field(default=None, description="Canonical URL or reference of questionnaire being answered")
    status: str = Field(default="completed", description="in-progress | completed | amended | entered-in-error | stopped")
    subject: Optional[FHIRReference] = Field(default=None, description="The subject of the questions (Patient)")
    encounter: Optional[FHIRReference] = Field(default=None, description="Encounter created as part of this response")
    authored: Optional[str] = Field(default=None, description="Date the answers were gathered")
    author: Optional[FHIRReference] = Field(default=None, description="Person who received and recorded the answers")
    item: list[FHIRQuestionnaireResponseItem] = Field(default_factory=list, description="Groups and questions")


class FHIRResearchStudy(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="ResearchStudy", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Business Identifier for study")
    title: Optional[str] = Field(default=None, description="Name for this study")
    status: str = Field(default="active", description="active | administratively-completed | approved | closed-to-accrual | closed-to-accrual-and-intervention | completed | disapproved | in-review | temporarily-closed-to-accrual | temporarily-closed-to-accrual-and-intervention | withdrawn")
    phase: Optional[FHIRCodeableConcept] = Field(default=None, description="n-a | early-phase-1 | phase-1 | phase-1-phase-2 | phase-2 | phase-2-phase-3 | phase-3 | phase-4")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Classifications for the study")
    condition: list[FHIRCodeableConcept] = Field(default_factory=list, description="Condition being studied")
    sponsor: Optional[FHIRReference] = Field(default=None, description="Organization that estimates and takes responsibility for the study")
    description: Optional[str] = Field(default=None, description="What this study is doing")


class FHIRProvenanceAgent(BaseModel):
    type: Optional[FHIRCodeableConcept] = Field(default=None, description="How the agent participated")
    role: list[FHIRCodeableConcept] = Field(default_factory=list, description="What the agents role was")
    who: FHIRReference = Field(..., description="Who participated (Practitioner, Device, Software)")


class FHIRProvenanceEntity(BaseModel):
    role: str = Field(default="derivation", description="derivation | revision | quotation | source | removal")
    what: FHIRReference = Field(..., description="Identity of entity (Observation, Encounter, Document)")


class FHIRProvenance(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Provenance", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    target: list[FHIRReference] = Field(default_factory=list, description="Target Reference(s) (e.g. Task, CarePlan)")
    recorded: str = Field(..., description="When the activity was recorded / evaluated")
    policy: list[str] = Field(default_factory=list, description="Policy under which the activity was defined")
    activity: Optional[FHIRCodeableConcept] = Field(default=None, description="Activity that occurred (e.g. multi-agent care coordination synthesis)")
    agent: list[FHIRProvenanceAgent] = Field(default_factory=list, description="Actor involved")
    entity: list[FHIRProvenanceEntity] = Field(default_factory=list, description="An entity used in this activity")
class FHIRImagingStudyInstance(BaseModel):
    uid: str = Field(..., description="DICOM SOP Instance UID")
    sopClass: Optional[FHIRCoding] = Field(default=None, description="DICOM class type")
    number: Optional[int] = Field(default=1, description="The number of this instance in the series")
    title: Optional[str] = Field(default=None, description="Description of instance")


class FHIRImagingStudySeries(BaseModel):
    uid: str = Field(..., description="DICOM Series Instance UID")
    number: Optional[int] = Field(default=1, description="Numeric identifier of this series")
    modality: FHIRCoding = Field(..., description="The modality of the instances in the series")
    description: Optional[str] = Field(default=None, description="A short description of the series")
    numberOfInstances: Optional[int] = Field(default=1, description="Number of series instances")
    bodySite: Optional[FHIRCoding] = Field(default=None, description="Body part examined")
    instance: list[FHIRImagingStudyInstance] = Field(default_factory=list, description="A single SOP instance")


class FHIRImagingStudy(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="ImagingStudy", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Accession number or study UID")
    status: str = Field(default="available", description="registered | available | cancelled | entered-in-error | unknown")
    modality: list[FHIRCoding] = Field(default_factory=list, description="All modalities in study")
    subject: FHIRReference = Field(..., description="Who or what the study is about (Patient)")
    encounter: Optional[FHIRReference] = Field(default=None, description="Encounter with which study is associated")
    started: Optional[str] = Field(default=None, description="When the study was started")
    basedOn: list[FHIRReference] = Field(default_factory=list, description="Order that generated study (ServiceRequest / ClinicalOrder)")
    referrer: Optional[FHIRReference] = Field(default=None, description="Referring physician")
    numberOfSeries: Optional[int] = Field(default=1, description="Number of Study Related Series")
    numberOfInstances: Optional[int] = Field(default=1, description="Number of Study Related Instances")
    description: Optional[str] = Field(default=None, description="Institution-generated description of the study")
    series: list[FHIRImagingStudySeries] = Field(default_factory=list, description="Each study has one or more series of instances")


# FHIR Consent & AuditEvent Models

class FHIRConsentProvision(BaseModel):
    type: str = Field(default="permit", description="deny | permit")
    period: Optional[FHIRPeriod] = Field(default=None, description="Timeframe for this provision")
    actor: list[dict[str, Any]] = Field(default_factory=list, description="Who is allowed or denied")
    action: list[FHIRCodeableConcept] = Field(default_factory=list, description="Actions permitted or denied")
    securityLabel: list[FHIRCoding] = Field(default_factory=list, description="Security Labels that define affected data")
    purpose: list[FHIRCoding] = Field(default_factory=list, description="Context of activities covered by this provision")
    class_: list[FHIRCoding] = Field(default_factory=list, alias="class", description="e.g. Resource Type, Document Type")


class FHIRConsentVerification(BaseModel):
    verified: bool = Field(default=True, description="Has verification taken place")
    verifiedWith: Optional[FHIRReference] = Field(default=None, description="Person who verified the consent")
    verificationDate: Optional[str] = Field(default=None, description="When consent verified")


class FHIRConsent(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="Consent", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    identifier: list[FHIRIdentifier] = Field(default_factory=list, description="Business identifier")
    status: str = Field(..., description="draft | proposed | active | rejected | inactive | entered-in-error")
    scope: FHIRCodeableConcept = Field(..., description="Which of the four realms is this consent for")
    category: list[FHIRCodeableConcept] = Field(default_factory=list, description="Classification of the consent statement")
    patient: FHIRReference = Field(..., description="Who the consent applies to")
    dateTime: Optional[str] = Field(default=None, description="When consent was agreed to")
    performer: list[FHIRReference] = Field(default_factory=list, description="Who is agreeing to the policy and provisions")
    organization: list[FHIRReference] = Field(default_factory=list, description="Custodian of the consent")
    policyRule: Optional[FHIRCodeableConcept] = Field(default=None, description="Regulation that this consent follows")
    verification: list[FHIRConsentVerification] = Field(default_factory=list, description="Consent Verified by patient or Legal Guardian")
    provision: Optional[FHIRConsentProvision] = Field(default=None, description="Constraints to the base Consent.policyRule")


class FHIRAuditEventAgent(BaseModel):
    type: Optional[FHIRCodeableConcept] = Field(default=None, description="How agent participated")
    role: list[FHIRCodeableConcept] = Field(default_factory=list, description="Agent role in the event")
    who: Optional[FHIRReference] = Field(default=None, description="Identifier of who")
    altId: Optional[str] = Field(default=None, description="Alternative User id e.g. login name")
    name: Optional[str] = Field(default=None, description="Human-meaningful name for the agent")
    requestor: bool = Field(default=True, description="Whether user is initiator")
    network: Optional[dict[str, Any]] = Field(default=None, description="Logical network location for application activity")


class FHIRAuditEventSource(BaseModel):
    site: Optional[str] = Field(default="MediGen-AI Clinical Cloud", description="Logical source location")
    observer: FHIRReference = Field(..., description="The identity of source detecting the event")
    type: list[FHIRCoding] = Field(default_factory=list, description="The type of source where event originated")


class FHIRAuditEventEntity(BaseModel):
    what: Optional[FHIRReference] = Field(default=None, description="Specific instance of resource")
    type: Optional[FHIRCoding] = Field(default=None, description="Type of entity involved")
    role: Optional[FHIRCoding] = Field(default=None, description="What role the entity played")
    name: Optional[str] = Field(default=None, description="Descriptor for entity")
    description: Optional[str] = Field(default=None, description="Descriptive text")
    detail: list[dict[str, Any]] = Field(default_factory=list, description="Additional Information about the entity")


class FHIRAuditEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    resourceType: str = Field(default="AuditEvent", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    type: FHIRCoding = Field(..., description="Type/identifier of event")
    subtype: list[FHIRCoding] = Field(default_factory=list, description="More specific type/id for the event")
    action: Optional[str] = Field(default=None, description="Type of action performed: C | R | U | D | E")
    period: Optional[FHIRPeriod] = Field(default=None, description="When the activity occurred")
    recorded: str = Field(..., description="Time when the event was recorded")
    outcome: Optional[str] = Field(default="0", description="Whether the event succeeded or failed (0=success, 4=minor fail, 8=serious fail, 12=major fail)")
    outcomeDesc: Optional[str] = Field(default=None, description="Description of the outcome")
    purposeOfEvent: list[FHIRCodeableConcept] = Field(default_factory=list, description="The purposeOfUse of the event")
    agent: list[FHIRAuditEventAgent] = Field(default_factory=list, description="Actor involved in the event")
    source: FHIRAuditEventSource = Field(..., description="Audit Event Reporter")
    entity: list[FHIRAuditEventEntity] = Field(default_factory=list, description="Data or updated entity")


# FHIR Bundle Models





class FHIRBundleEntryRequest(BaseModel):
    method: str = Field(default="POST", description="GET | HEAD | POST | PUT | DELETE | PATCH")
    url: str = Field(..., description="URL for request")


class FHIRBundleEntry(BaseModel):
    fullUrl: Optional[str] = Field(default=None, description="URI for entry")
    resource: Optional[dict[str, Any]] = Field(default=None, description="A resource in the bundle")
    request: Optional[FHIRBundleEntryRequest] = Field(default=None, description="Transaction/batch request")


class FHIRBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    resourceType: str = Field(default="Bundle", description="FHIR resource type")
    id: Optional[str] = Field(default=None, description="Logical id of this artifact")
    type: str = Field(default="collection", description="document | message | transaction | transaction-response | batch | batch-response | history | searchset | collection")
    timestamp: Optional[str] = Field(default=None, description="When the bundle was assembled")
    total: Optional[int] = Field(default=None, description="If searchset, total number of matches")
    entry: list[FHIRBundleEntry] = Field(default_factory=list, description="Entry in the bundle - will have a resource or information about a resource")


# Import / Operation Schemas

class FHIRImportResult(BaseModel):
    success: bool = Field(..., description="Whether the import operation succeeded")
    resource_type: str = Field(..., description="Type of the imported FHIR resource")
    resource_id: Optional[str] = Field(default=None, description="ID of the FHIR resource")
    internal_id: Optional[str] = Field(default=None, description="Internal MediGen-AI identifier (e.g. PAT-..., ENC-...)")
    status: str = Field(..., description="created | updated | skipped | failed")
    message: str = Field(..., description="Human-readable result summary")
    validation_errors: list[str] = Field(default_factory=list, description="Validation issues if any")


class FHIRBatchImportResponse(BaseModel):
    success: bool = Field(..., description="Overall batch status")
    imported: int = Field(default=0, description="Total successfully imported resources")
    skipped: int = Field(default=0, description="Total skipped resources")
    failed: int = Field(default=0, description="Total failed resources")
    results: list[FHIRImportResult] = Field(default_factory=list, description="Individual resource results")
    errors: list[str] = Field(default_factory=list, description="Batch-level error messages if any")


# FHIR CapabilityStatement (Phase 9.0.20)

class FHIRCapabilityInteraction(BaseModel):
    code: str = Field(..., description="read | vread | update | patch | delete | history-instance | history-type | create | search-type")
    documentation: Optional[str] = Field(default=None, description="What this interaction entails")


class FHIRCapabilityResource(BaseModel):
    type: str = Field(..., description="Resource Type (Patient, Encounter, etc.)")
    profile: Optional[str] = Field(default=None, description="Base System Profile")
    interaction: list[FHIRCapabilityInteraction] = Field(default_factory=list, description="Supported operations")
    searchParam: list[dict[str, str]] = Field(default_factory=list, description="Search parameters for this resource")


class FHIRCapabilityRest(BaseModel):
    mode: str = Field(default="server", description="client | server")
    documentation: Optional[str] = Field(default=None, description="General description of implementation")
    security: Optional[dict[str, Any]] = Field(default=None, description="Information about security of implementation")
    resource: list[FHIRCapabilityResource] = Field(default_factory=list, description="Resource supported by the server")


class FHIRCapabilityStatement(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    resourceType: str = Field(default="CapabilityStatement", description="FHIR resource type")
    id: Optional[str] = Field(default="medigen-ai-capability-statement", description="Logical id")
    status: str = Field(default="active", description="draft | active | retired | unknown")
    date: str = Field(..., description="Date this statement was published")
    publisher: Optional[str] = Field(default="MediGen AI Clinical Intelligence Platform")
    kind: str = Field(default="instance", description="instance | capability | requirements")
    software: Optional[dict[str, str]] = Field(default=None, description="Software that is covered by this statement")
    implementation: Optional[dict[str, str]] = Field(default=None, description="If this describes a specific instance")
    fhirVersion: str = Field(default="4.0.1", description="FHIR Version (4.0.1)")
    format: list[str] = Field(default=["application/fhir+json", "application/json"], description="formats supported (xml | json | etc.)")
    rest: list[FHIRCapabilityRest] = Field(default_factory=list, description="If the endpoint is a RESTful one")

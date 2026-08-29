from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional

from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.cohort import CohortMembership, PatientCohort
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.patient import Patient
from app.models.risk_assessment import ClinicalRiskAssessment
from app.schemas.encounter import EncounterCreate, EncounterStatus, EncounterType
from app.schemas.fhir import (
    FHIRAddress,
    FHIRAnnotation,
    FHIRCarePlan,
    FHIRCarePlanActivity,
    FHIRCarePlanActivityDetail,
    FHIRCodeableConcept,
    FHIRCoding,
    FHIRCommunication,
    FHIRComposition,
    FHIRCompositionSection,
    FHIRContactPoint,
    FHIRDosage,
    FHIREncounter,
    FHIREncounterDiagnosis,
    FHIRGoal,
    FHIRGroup,
    FHIRGroupMember,
    FHIRHumanName,
    FHIRIdentifier,
    FHIRMedicationStatement,
    FHIRObservation,
    FHIRPatient,
    FHIRPatientContact,
    FHIRPeriod,
    FHIRQuantity,
    FHIRReference,
    FHIRCondition,
    FHIRRiskAssessment,
    FHIRRiskAssessmentPrediction,
    FHIRTask,
)


from app.schemas.patient import Gender, PatientCreate, PatientStatus


class BaseFHIRMapper(ABC):
    """Base abstract interface for FHIR R4 bidirectional mapping."""
    pass


class FHIRPatientMapper(BaseFHIRMapper):
    """Bidirectional mapper between internal Patient ORM model and FHIR R4 Patient resource."""

    @staticmethod
    def to_fhir(patient: Patient) -> FHIRPatient:
        """Convert internal Patient ORM model to FHIR R4 Patient schema."""
        # Administrative Gender mapping
        gender_str = "unknown"
        if patient.gender == Gender.MALE:
            gender_str = "male"
        elif patient.gender == Gender.FEMALE:
            gender_str = "female"
        elif patient.gender == Gender.OTHER:
            gender_str = "other"

        telecom: list[FHIRContactPoint] = []
        if patient.phone:
            telecom.append(FHIRContactPoint(system="phone", value=patient.phone, use="mobile"))
        if patient.email:
            telecom.append(FHIRContactPoint(system="email", value=patient.email, use="home"))

        addresses: list[FHIRAddress] = []
        if patient.address:
            addresses.append(FHIRAddress(use="home", type="both", text=patient.address, line=[patient.address]))

        contacts: list[FHIRPatientContact] = []
        if patient.emergency_contact_name or patient.emergency_contact_phone:
            c_name = None
            if patient.emergency_contact_name:
                parts = patient.emergency_contact_name.strip().split(" ", 1)
                c_name = FHIRHumanName(
                    use="usual",
                    family=parts[1] if len(parts) > 1 else "",
                    given=[parts[0]],
                    text=patient.emergency_contact_name,
                )
            c_telecom: list[FHIRContactPoint] = []
            if patient.emergency_contact_phone:
                c_telecom.append(FHIRContactPoint(system="phone", value=patient.emergency_contact_phone, use="mobile"))

            contacts.append(
                FHIRPatientContact(
                    relationship=[
                        FHIRCodeableConcept(
                            coding=[
                                FHIRCoding(
                                    system="http://terminology.hl7.org/CodeSystem/v2-0131",
                                    code="C",
                                    display="Emergency Contact",
                                )
                            ],
                            text="Emergency Contact",
                        )
                    ],
                    name=c_name,
                    telecom=c_telecom,
                )
            )

        return FHIRPatient(
            id=patient.patient_id,
            identifier=[
                FHIRIdentifier(
                    use="official",
                    system="https://medigen.ai/fhir/patient-id",
                    value=patient.patient_id,
                )
            ],
            active=(patient.status == PatientStatus.ACTIVE),
            name=[
                FHIRHumanName(
                    use="official",
                    family=patient.last_name,
                    given=[patient.first_name],
                    text=f"{patient.first_name} {patient.last_name}",
                )
            ],
            telecom=telecom,
            gender=gender_str,
            birthDate=patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            address=addresses,
            contact=contacts,
        )

    @staticmethod
    def to_internal(fhir_data: dict[str, Any] | FHIRPatient) -> PatientCreate:
        """Convert FHIR R4 Patient resource into internal PatientCreate schema."""
        if isinstance(fhir_data, FHIRPatient):
            raw = fhir_data.model_dump(exclude_none=True)
        else:
            raw = dict(fhir_data)

        # Extract names
        first_name = "Unknown"
        last_name = "Patient"
        names = raw.get("name", [])
        if names and isinstance(names, list) and isinstance(names[0], dict):
            name_obj = names[0]
            family = name_obj.get("family")
            given = name_obj.get("given", [])
            text = name_obj.get("text")
            if family:
                last_name = family.strip()
            if given and isinstance(given, list) and given[0]:
                first_name = str(given[0]).strip()
            elif text:
                parts = text.strip().split(" ", 1)
                first_name = parts[0]
                if len(parts) > 1:
                    last_name = parts[1]

        # Extract DOB
        birth_str = raw.get("birthDate")
        dob = date(1970, 1, 1)
        if birth_str:
            try:
                dob = date.fromisoformat(str(birth_str).strip()[:10])
            except ValueError:
                pass

        # Extract Gender
        gender_val = Gender.OTHER
        g_raw = str(raw.get("gender", "")).lower()
        if g_raw == "male":
            gender_val = Gender.MALE
        elif g_raw == "female":
            gender_val = Gender.FEMALE

        # Extract Telecom
        phone = None
        email = None
        for tc in raw.get("telecom", []):
            if isinstance(tc, dict):
                sys = tc.get("system")
                val = tc.get("value")
                if sys == "phone" and val and not phone:
                    phone = str(val).strip()
                elif sys == "email" and val and not email:
                    email = str(val).strip()

        # Extract Address
        address = None
        addresses = raw.get("address", [])
        if addresses and isinstance(addresses, list) and isinstance(addresses[0], dict):
            addr_obj = addresses[0]
            if addr_obj.get("text"):
                address = addr_obj.get("text")
            elif addr_obj.get("line"):
                address = ", ".join(addr_obj.get("line"))

        # Extract Contact
        em_name = None
        em_phone = None
        contacts = raw.get("contact", [])
        if contacts and isinstance(contacts, list) and isinstance(contacts[0], dict):
            c_obj = contacts[0]
            if c_obj.get("name") and isinstance(c_obj["name"], dict):
                em_name = c_obj["name"].get("text") or c_obj["name"].get("family")
            for c_tc in c_obj.get("telecom", []):
                if isinstance(c_tc, dict) and c_tc.get("system") == "phone":
                    em_phone = c_tc.get("value")
                    break

        status_val = PatientStatus.ACTIVE if raw.get("active", True) else PatientStatus.INACTIVE
        patient_id_candidate = raw.get("id")

        return PatientCreate(
            patient_id=patient_id_candidate,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            gender=gender_val,
            phone=phone,
            email=email,
            address=address,
            emergency_contact_name=em_name,
            emergency_contact_phone=em_phone,
            status=status_val,
        )


class FHIREncounterMapper(BaseFHIRMapper):
    """Bidirectional mapper between internal Encounter ORM model and FHIR R4 Encounter resource."""

    @staticmethod
    def to_fhir(encounter: Encounter, patient: Patient) -> FHIREncounter:
        """Convert internal Encounter ORM model to FHIR R4 Encounter resource."""
        # Status mapping
        status_str = "finished"
        if encounter.status == EncounterStatus.IN_PROGRESS:
            status_str = "in-progress"
        elif encounter.status == EncounterStatus.CANCELLED:
            status_str = "cancelled"
        elif encounter.status == EncounterStatus.AMENDED:
            status_str = "finished"

        # Diagnose items
        diagnoses: list[FHIREncounterDiagnosis] = []
        if encounter.assessment:
            diagnoses.append(
                FHIREncounterDiagnosis(
                    condition=FHIRReference(
                        display=encounter.assessment,
                    ),
                    use=FHIRCodeableConcept(
                        coding=[
                            FHIRCoding(
                                system="http://terminology.hl7.org/CodeSystem/diagnosis-role",
                                code="DD",
                                display="Discharge diagnosis",
                            )
                        ],
                        text="Discharge diagnosis",
                    ),
                    rank=1,
                )
            )

        return FHIREncounter(
            id=encounter.encounter_id,
            identifier=[
                FHIRIdentifier(
                    use="official",
                    system="https://medigen.ai/fhir/encounter-id",
                    value=encounter.encounter_id,
                )
            ],
            status=status_str,
            class_=FHIRCoding(
                system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                code="AMB",
                display="ambulatory",
            ),
            type=[
                FHIRCodeableConcept(
                    coding=[
                        FHIRCoding(
                            system="https://medigen.ai/fhir/encounter-type",
                            code=encounter.encounter_type.value,
                            display=encounter.encounter_type.value.replace("_", " ").title(),
                        )
                    ],
                    text=encounter.chief_complaint,
                )
            ],
            subject=FHIRReference(
                reference=f"Patient/{patient.patient_id}",
                display=f"{patient.first_name} {patient.last_name}",
            ),
            period=FHIRPeriod(
                start=encounter.encounter_date.isoformat() if encounter.encounter_date else None,
            ),
            reasonCode=[
                FHIRCodeableConcept(
                    text=encounter.chief_complaint,
                )
            ],
            diagnosis=diagnoses,
        )

    @staticmethod
    def to_internal(fhir_data: dict[str, Any] | FHIREncounter) -> tuple[EncounterCreate, str]:
        """Convert FHIR R4 Encounter into internal EncounterCreate schema and target patient_id."""
        if isinstance(fhir_data, FHIREncounter):
            raw = fhir_data.model_dump(exclude_none=True)
        else:
            raw = dict(fhir_data)

        # Extract target patient reference
        patient_ref = ""
        subject = raw.get("subject", {})
        if isinstance(subject, dict) and subject.get("reference"):
            ref_str = str(subject["reference"])
            patient_ref = ref_str.split("/")[-1].strip()

        # Extract Chief Complaint & Type
        chief_complaint = "Routine consultation"
        reasons = raw.get("reasonCode", [])
        if reasons and isinstance(reasons, list) and isinstance(reasons[0], dict):
            chief_complaint = reasons[0].get("text") or chief_complaint

        enc_type = EncounterType.INITIAL_CONSULTATION
        types = raw.get("type", [])
        if types and isinstance(types, list) and isinstance(types[0], dict):
            coding_list = types[0].get("coding", [])
            if coding_list and isinstance(coding_list, list) and isinstance(coding_list[0], dict):
                code_val = coding_list[0].get("code")
                for e_type in EncounterType:
                    if e_type.value == code_val:
                        enc_type = e_type
                        break

        # Extract Assessment / Diagnosis
        assessment = None
        diagnoses = raw.get("diagnosis", [])
        if diagnoses and isinstance(diagnoses, list) and isinstance(diagnoses[0], dict):
            cond_ref = diagnoses[0].get("condition", {})
            if isinstance(cond_ref, dict):
                assessment = cond_ref.get("display")

        # Extract Status
        status_val = EncounterStatus.COMPLETED
        f_status = raw.get("status", "")
        if f_status in {"in-progress", "triaged", "arrived"}:
            status_val = EncounterStatus.IN_PROGRESS
        elif f_status == "cancelled":
            status_val = EncounterStatus.CANCELLED

        # Extract Date
        period = raw.get("period", {})
        enc_date = None
        if isinstance(period, dict) and period.get("start"):
            try:
                enc_date = datetime.fromisoformat(str(period["start"]).replace("Z", "+00:00"))
            except ValueError:
                pass

        encounter_create = EncounterCreate(
            encounter_type=enc_type,
            chief_complaint=chief_complaint,
            clinical_notes=f"Imported via FHIR R4 Encounter resource (id: {raw.get('id', 'N/A')}).",
            assessment=assessment,
            plan=None,
            status=status_val,
            encounter_date=enc_date,
        )
        return encounter_create, patient_ref


class FHIRConditionMapper(BaseFHIRMapper):
    """Mapper for FHIR R4 Condition resources representing clinical diagnoses."""

    @staticmethod
    def to_fhir(
        condition_id: str,
        diagnosis_title: str,
        patient_id: str,
        encounter_id: Optional[str] = None,
        clinical_status: str = "active",
        recorded_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> FHIRCondition:
        """Construct FHIR R4 Condition resource."""
        annotations: list[FHIRAnnotation] = []
        if notes:
            annotations.append(FHIRAnnotation(text=notes, time=recorded_date.isoformat() if recorded_date else None))

        enc_ref = FHIRReference(reference=f"Encounter/{encounter_id}") if encounter_id else None

        return FHIRCondition(
            id=condition_id,
            identifier=[
                FHIRIdentifier(
                    use="official",
                    system="https://medigen.ai/fhir/condition-id",
                    value=condition_id,
                )
            ],
            clinicalStatus=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                        code=clinical_status,
                        display=clinical_status.capitalize(),
                    )
                ],
                text=clinical_status.capitalize(),
            ),
            verificationStatus=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        code="confirmed",
                        display="Confirmed",
                    )
                ],
                text="Confirmed",
            ),
            category=[
                FHIRCodeableConcept(
                    coding=[
                        FHIRCoding(
                            system="http://terminology.hl7.org/CodeSystem/condition-category",
                            code="encounter-diagnosis",
                            display="Encounter Diagnosis",
                        )
                    ],
                    text="Encounter Diagnosis",
                )
            ],
            code=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://snomed.info/sct",
                        display=diagnosis_title,
                    )
                ],
                text=diagnosis_title,
            ),
            subject=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            encounter=enc_ref,
            recordedDate=recorded_date.isoformat() if recorded_date else None,
            note=annotations,
        )


class FHIRMedicationStatementMapper(BaseFHIRMapper):
    """Mapper for FHIR R4 MedicationStatement resources."""

    @staticmethod
    def to_fhir(
        medication_id: str,
        medication_name: str,
        patient_id: str,
        status: str = "active",
        effective_date: Optional[datetime] = None,
        dosage_text: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FHIRMedicationStatement:
        """Construct FHIR R4 MedicationStatement resource."""
        dosages: list[FHIRDosage] = []
        if dosage_text:
            dosages.append(FHIRDosage(text=dosage_text))

        annotations: list[FHIRAnnotation] = []
        if notes:
            annotations.append(FHIRAnnotation(text=notes))

        return FHIRMedicationStatement(
            id=medication_id,
            identifier=[
                FHIRIdentifier(
                    use="official",
                    system="https://medigen.ai/fhir/medication-statement-id",
                    value=medication_id,
                )
            ],
            status=status,
            medicationCodeableConcept=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://www.nlm.nih.gov/research/umls/rxnorm",
                        display=medication_name,
                    )
                ],
                text=medication_name,
            ),
            subject=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            effectiveDateTime=effective_date.isoformat() if effective_date else None,
            dosage=dosages,
            note=annotations,
        )


class FHIRObservationMapper(BaseFHIRMapper):
    """Mapper for FHIR R4 Observation resources (vitals, lab results)."""

    @staticmethod
    def to_fhir(
        observation_id: str,
        test_name: str,
        patient_id: str,
        value_quantity: Optional[float] = None,
        unit: Optional[str] = None,
        value_string: Optional[str] = None,
        status: str = "final",
        category_code: str = "laboratory",
        effective_date: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> FHIRObservation:
        """Construct FHIR R4 Observation resource."""
        q_val = None
        if value_quantity is not None:
            q_val = FHIRQuantity(value=value_quantity, unit=unit)

        annotations: list[FHIRAnnotation] = []
        if notes:
            annotations.append(FHIRAnnotation(text=notes))

        return FHIRObservation(
            id=observation_id,
            identifier=[
                FHIRIdentifier(
                    use="official",
                    system="https://medigen.ai/fhir/observation-id",
                    value=observation_id,
                )
            ],
            status=status,
            category=[
                FHIRCodeableConcept(
                    coding=[
                        FHIRCoding(
                            system="http://terminology.hl7.org/CodeSystem/observation-category",
                            code=category_code,
                            display=category_code.capitalize(),
                        )
                    ],
                    text=category_code.capitalize(),
                )
            ],
            code=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://loinc.org",
                        display=test_name,
                    )
                ],
                text=test_name,
            ),
            subject=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            effectiveDateTime=effective_date.isoformat() if effective_date else None,
            valueQuantity=q_val,
            valueString=value_string,
            note=annotations,
        )


class FHIRGoalMapper(BaseFHIRMapper):
    """Mapper from internal goal dictionary to FHIR R4 Goal resource."""

    @staticmethod
    def to_fhir(goal_dict: dict[str, Any], patient_id: str) -> FHIRGoal:
        goal_id = goal_dict.get("goal_id", "G-01")
        title = goal_dict.get("title", "Clinical Health Goal")
        metric = goal_dict.get("target_metric")
        target_text = f"{title}: {metric}" if metric else title

        return FHIRGoal(
            id=goal_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/goals",
                    value=goal_id,
                )
            ],
            lifecycleStatus=goal_dict.get("status", "active"),
            description=FHIRCodeableConcept(
                text=target_text,
                coding=[
                    FHIRCoding(
                        system="http://snomed.info/sct",
                        display=title,
                    )
                ],
            ),
            subject=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            targetDate=str(goal_dict.get("target_date")) if goal_dict.get("target_date") else None,
        )


class FHIRTaskMapper(BaseFHIRMapper):
    """Mapper from internal CareTask ORM to FHIR R4 Task resource."""

    @staticmethod
    def to_fhir(task: CareTask, patient_id: str) -> FHIRTask:
        status_map = {
            "pending": "requested",
            "in_progress": "in-progress",
            "completed": "completed",
            "cancelled": "cancelled",
        }
        fhir_status = status_map.get(task.status.value if hasattr(task.status, "value") else str(task.status), "requested")
        priority_str = (task.priority.value if hasattr(task.priority, "value") else str(task.priority)).lower()

        return FHIRTask(
            id=task.task_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/tasks",
                    value=task.task_id,
                )
            ],
            status=fhir_status,
            intent="order",
            priority=priority_str,
            description=task.title,
            for_reference=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            executionPeriod=FHIRPeriod(
                end=task.due_date.isoformat() if task.due_date else None,
            ),
            authoredOn=task.created_at.isoformat() if task.created_at else None,
        )


class FHIRCarePlanMapper(BaseFHIRMapper):
    """Bidirectional mapper between internal CarePlan ORM and FHIR R4 CarePlan."""

    @staticmethod
    def to_fhir(plan: CarePlan, patient_id: str) -> FHIRCarePlan:
        status_map = {
            "draft": "draft",
            "reviewed": "draft",
            "active": "active",
            "completed": "completed",
            "suspended": "on-hold",
            "cancelled": "revoked",
        }
        fhir_status = status_map.get(plan.status.value if hasattr(plan.status, "value") else str(plan.status), "draft")
        category_str = plan.category.value if hasattr(plan.category, "value") else str(plan.category)

        activities: list[FHIRCarePlanActivity] = []
        if plan.interventions_json:
            for intervention in plan.interventions_json:
                desc = intervention.get("description", "Clinical intervention")
                act_detail = FHIRCarePlanActivityDetail(
                    kind="ServiceRequest",
                    status="in-progress" if fhir_status == "active" else "not-started",
                    description=desc,
                    code=FHIRCodeableConcept(
                        text=desc,
                        coding=[
                            FHIRCoding(
                                system="http://snomed.info/sct",
                                display=desc,
                            )
                        ],
                    ),
                )
                activities.append(FHIRCarePlanActivity(detail=act_detail))

        goals_refs: list[FHIRReference] = []
        if plan.goals_json:
            for g in plan.goals_json:
                gid = g.get("goal_id", "G-01")
                gtitle = g.get("title", "Clinical Goal")
                goals_refs.append(FHIRReference(reference=f"Goal/{gid}", display=gtitle))

        return FHIRCarePlan(
            id=plan.plan_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/care-plans",
                    value=plan.plan_id,
                )
            ],
            status=fhir_status,
            intent=plan.intent or "plan",
            category=[
                FHIRCodeableConcept(
                    text=category_str.replace("_", " ").title(),
                    coding=[
                        FHIRCoding(
                            system="http://hl7.org/fhir/us/core/CodeSystem/careplan-category",
                            code=category_str,
                            display=category_str.replace("_", " ").title(),
                        )
                    ],
                )
            ],
            title=plan.title,
            description=plan.description,
            subject=FHIRReference(
                reference=f"Patient/{patient_id}",
            ),
            period=FHIRPeriod(
                start=plan.start_date.isoformat() if plan.start_date else None,
                end=plan.end_date.isoformat() if plan.end_date else None,
            ),
            goal=goals_refs,
            activity=activities,
        )


class FHIRGroupMapper(BaseFHIRMapper):
    """Mapper converting PatientCohort and active memberships to FHIR R4 Group resource."""

    @staticmethod
    def to_fhir(cohort: PatientCohort, members: list[CohortMembership]) -> FHIRGroup:
        member_entries: list[FHIRGroupMember] = []
        for m in members:
            pat_id = m.patient.patient_id if m.patient else f"PAT-{m.patient_id}"
            member_entries.append(
                FHIRGroupMember(
                    entity=FHIRReference(
                        reference=f"Patient/{pat_id}",
                        display=f"{m.patient.first_name} {m.patient.last_name}" if m.patient else None,
                    ),
                    inactive=(m.status != "active"),
                )
            )

        return FHIRGroup(
            id=cohort.cohort_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/cohorts",
                    value=cohort.cohort_id,
                )
            ],
            active=True,
            type="person",
            actual=True,
            name=cohort.name,
            quantity=len(member_entries),
            member=member_entries,
        )


class FHIRRiskAssessmentMapper(BaseFHIRMapper):
    """Mapper converting ClinicalRiskAssessment to standard FHIR R4 RiskAssessment resource."""

    @staticmethod
    def to_fhir(assessment: ClinicalRiskAssessment, patient_id_str: str) -> FHIRRiskAssessment:
        risk_type_str = assessment.risk_type or "clinical_risk"
        outcome_concept = FHIRCodeableConcept(
            text=assessment.predicted_outcome or risk_type_str.replace("_", " ").title(),
            coding=[
                FHIRCoding(
                    system="http://medigen.ai/fhir/risk-types",
                    code=risk_type_str,
                    display=risk_type_str.replace("_", " ").title(),
                )
            ],
        )

        tier_concept = FHIRCodeableConcept(
            text=assessment.risk_tier or "MODERATE",
            coding=[
                FHIRCoding(
                    system="http://terminology.hl7.org/CodeSystem/risk-probability",
                    code=(assessment.risk_tier or "MODERATE").lower(),
                    display=assessment.risk_tier or "MODERATE",
                )
            ],
        )

        # Serialize mitigation recommendation notes
        mitigation_text = None
        if assessment.mitigation_recommendations_json:
            mitigation_text = "; ".join(
                f"[{m.get('priority', 'ROUTINE')}] {m.get('action_title', '')}"
                for m in assessment.mitigation_recommendations_json
                if isinstance(m, dict) and m.get("action_title")
            )

        return FHIRRiskAssessment(
            id=assessment.assessment_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/risk-assessments",
                    value=assessment.assessment_id,
                )
            ],
            status="final",
            subject=FHIRReference(reference=f"Patient/{patient_id_str}"),
            encounter=FHIRReference(reference=f"Encounter/{assessment.encounter_id}") if assessment.encounter_id else None,
            occurrenceDateTime=assessment.assessed_at.isoformat() if assessment.assessed_at else None,
            prediction=[
                FHIRRiskAssessmentPrediction(
                    outcome=outcome_concept,
                    probabilityDecimal=assessment.risk_score,
                    qualitativeRisk=tier_concept,
                    rationale=f"Quantitative risk score: {assessment.risk_score}/100 ({assessment.risk_tier})",
                )
            ],
            mitigation=mitigation_text,
        )


class FHIRCompositionMapper(BaseFHIRMapper):
    """Maps internal DischargeProtocol to standard FHIR R4 Composition resource."""

    @staticmethod
    def to_fhir(discharge: DischargeProtocol, patient_id_str: str) -> FHIRComposition:
        sections = [
            FHIRCompositionSection(
                title="Hospital Course",
                code=FHIRCodeableConcept(
                    coding=[FHIRCoding(system="http://loinc.org", code="8648-8", display="Hospital Course Narrative")]
                ),
                text={"status": "generated", "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{discharge.hospital_course_summary}</p></div>"},
            ),
            FHIRCompositionSection(
                title="Discharge Diagnoses",
                code=FHIRCodeableConcept(
                    coding=[FHIRCoding(system="http://loinc.org", code="11535-2", display="Hospital Discharge Diagnosis")]
                ),
                text={
                    "status": "generated",
                    "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p><strong>Primary:</strong> {discharge.primary_discharge_diagnosis}</p></div>",
                },
            ),
        ]

        if discharge.medication_reconciliation_json:
            med_lines = "; ".join(
                f"{m.get('medication_name', '')} ({m.get('dose', '')} {m.get('frequency', '')}) - [{m.get('reconciliation_status', '')}]"
                for m in discharge.medication_reconciliation_json
                if isinstance(m, dict)
            )
            sections.append(
                FHIRCompositionSection(
                    title="Discharge Medications",
                    code=FHIRCodeableConcept(
                        coding=[FHIRCoding(system="http://loinc.org", code="10183-2", display="Hospital Discharge Medications")]
                    ),
                    text={"status": "generated", "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{med_lines}</p></div>"},
                )
            )

        if discharge.warning_symptoms_json:
            warn_lines = "; ".join(
                f"{w.get('symptom_title', '')} ({w.get('urgency_level', '')})"
                for w in discharge.warning_symptoms_json
                if isinstance(w, dict)
            )
            sections.append(
                FHIRCompositionSection(
                    title="Warning Signs & Red Flags",
                    code=FHIRCodeableConcept(
                        coding=[FHIRCoding(system="http://loinc.org", code="8653-8", display="Hospital Discharge Instructions")]
                    ),
                    text={"status": "generated", "div": f"<div xmlns=\"http://www.w3.org/1999/xhtml\"><p>{warn_lines}</p></div>"},
                )
            )

        authors = []
        if discharge.attending_user_id:
            authors.append(FHIRReference(reference=f"Practitioner/{discharge.attending_user_id}"))

        return FHIRComposition(
            id=discharge.discharge_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/discharge-protocols",
                    value=discharge.discharge_id,
                )
            ],
            status="final" if discharge.status in ("ready_for_discharge", "completed") else "preliminary",
            type=FHIRCodeableConcept(
                coding=[
                    FHIRCoding(
                        system="http://loinc.org",
                        code="18842-5",
                        display="Discharge Summary",
                    )
                ],
                text="Discharge Summary & Protocol",
            ),
            category=[
                FHIRCodeableConcept(
                    coding=[
                        FHIRCoding(
                            system="http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                            code="clinical-note",
                            display="Clinical Note",
                        )
                    ]
                )
            ],
            subject=FHIRReference(reference=f"Patient/{patient_id_str}"),
            encounter=FHIRReference(reference=f"Encounter/{discharge.encounter_id}") if discharge.encounter_id else None,
            date=discharge.discharge_date.isoformat() if discharge.discharge_date else discharge.created_at.isoformat(),
            author=authors,
            title=f"Discharge Summary for {patient_id_str} ({discharge.disposition.replace('_', ' ').title()})",
            section=sections,
        )


class FHIRCommunicationMapper(BaseFHIRMapper):
    """Maps internal ClinicalHandoff to standard FHIR R4 Communication resource."""

    @staticmethod
    def to_fhir(handoff: ClinicalHandoff, patient_id_str: str) -> FHIRCommunication:
        recipients = []
        if handoff.receiver_user_id:
            recipients.append(FHIRReference(reference=f"Practitioner/{handoff.receiver_user_id}"))

        payload_items = [
            {"contentString": f"[{handoff.framework.upper()}] {handoff.summary}"}
        ]
        if handoff.action_items_json:
            payload_items.append({"actionItems": handoff.action_items_json})
        if handoff.situational_awareness_json:
            payload_items.append({"contingencyPlans": handoff.situational_awareness_json})

        return FHIRCommunication(
            id=handoff.handoff_id,
            identifier=[
                FHIRIdentifier(
                    system="http://medigen.ai/fhir/clinical-handoffs",
                    value=handoff.handoff_id,
                )
            ],
            status="completed" if handoff.status in ("acknowledged", "completed") else "in-progress",
            category=[
                FHIRCodeableConcept(
                    coding=[
                        FHIRCoding(
                            system="http://terminology.hl7.org/CodeSystem/communication-category",
                            code="clinical-handoff",
                            display=f"Clinical Handoff ({handoff.handoff_type})",
                        )
                    ]
                )
            ],
            priority="urgent" if handoff.illness_severity in ("watcher", "unstable") else "routine",
            subject=FHIRReference(reference=f"Patient/{patient_id_str}"),
            encounter=FHIRReference(reference=f"Encounter/{handoff.encounter_id}") if handoff.encounter_id else None,
            sent=handoff.created_at.isoformat() if handoff.created_at else None,
            received=handoff.acknowledged_at.isoformat() if handoff.acknowledged_at else None,
            sender=FHIRReference(reference=f"Practitioner/{handoff.sender_user_id}") if handoff.sender_user_id else None,
            recipient=recipients,
            payload=payload_items,
        )

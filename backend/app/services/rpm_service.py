"""Service layer for Remote Patient Monitoring (RPM), PROMs & Telehealth.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
from typing import Any, Optional
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai.rpm_provider import MockRPMProvider
from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.patient import Patient

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
from app.models.user import User
from app.schemas.alert import AlertSeverity, AlertStatus
from app.schemas.care_plan import CarePlanCategory, CarePlanStatus
from app.schemas.care_task import CareTaskStatus, CareTaskType, TaskPriority
from app.schemas.rpm import (

    ObservationClassification,
    PROMDefinitionResponse,
    PROMResponseDetail,
    PROMResponseSubmitRequest,
    RPMDeviceCreate,
    RPMDeviceResponse,
    RPMEscalationAcknowledgeRequest,
    RPMEscalationAlertResponse,
    RPMEscalationResolveRequest,
    RPMObservationCreate,
    RPMObservationResponse,
    RPMProgramEnrollRequest,
    RPMProgramResponse,
    RPMTelemetrySummary,
    RPMThresholdRuleCreate,
    RPMThresholdRuleResponse,
    TelehealthSessionCreate,
    TelehealthSessionResponse,
    TelehealthSessionUpdate,
    TelehealthStatus,
)
from app.schemas.user import UserRole

logger = logging.getLogger("medigen.services.rpm_service")

# Singleton Provider
rpm_provider = MockRPMProvider()


# ==============================================================================
# SEEDING DEFAULT PROMS
# ==============================================================================

DEFAULT_PROMS = [
    {
        "prom_id": "PROM-PHQ9",
        "title": "Patient Health Questionnaire (PHQ-9)",
        "domain": "mental_health",
        "version": "2026.1",
        "scoring_method": "sum_total",
        "questions_json": [
            {
                "id": "1",
                "prompt": "Little interest or pleasure in doing things",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "2",
                "prompt": "Feeling down, depressed, or hopeless",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "3",
                "prompt": "Trouble falling or staying asleep, or sleeping too much",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "4",
                "prompt": "Feeling tired or having little energy",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "5",
                "prompt": "Poor appetite or overeating",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "6",
                "prompt": "Feeling bad about yourself or that you are a failure",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "7",
                "prompt": "Trouble concentrating on things such as reading or television",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "8",
                "prompt": "Moving or speaking slowly, or fidgety/restless",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "9",
                "prompt": "Thoughts that you would be better off dead or hurting yourself",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
        ],
        "interpretation_ranges_json": [
            {"min": 0, "max": 4, "severity": "MINIMAL", "clinical_summary": "Minimal or no depression"},
            {"min": 5, "max": 9, "severity": "MILD", "clinical_summary": "Mild depression symptoms"},
            {"min": 10, "max": 14, "severity": "MODERATE", "clinical_summary": "Moderate depression symptoms"},
            {"min": 15, "max": 19, "severity": "MODERATELY_SEVERE", "clinical_summary": "Moderately severe depression"},
            {"min": 20, "max": 27, "severity": "SEVERE", "clinical_summary": "Severe depression symptoms"},
        ],
    },
    {
        "prom_id": "PROM-GAD7",
        "title": "Generalized Anxiety Disorder (GAD-7)",
        "domain": "mental_health",
        "version": "2026.1",
        "scoring_method": "sum_total",
        "questions_json": [
            {
                "id": "1",
                "prompt": "Feeling nervous, anxious, or on edge",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "2",
                "prompt": "Not being able to stop or control worrying",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "3",
                "prompt": "Worrying too much about different things",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "4",
                "prompt": "Trouble relaxing",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "5",
                "prompt": "Being so restless that it is hard to sit still",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "6",
                "prompt": "Becoming easily annoyed or irritable",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
            {
                "id": "7",
                "prompt": "Feeling afraid as if something awful might happen",
                "options": [
                    {"label": "Not at all", "score": 0},
                    {"label": "Several days", "score": 1},
                    {"label": "More than half the days", "score": 2},
                    {"label": "Nearly every day", "score": 3},
                ],
            },
        ],
        "interpretation_ranges_json": [
            {"min": 0, "max": 4, "severity": "MINIMAL", "clinical_summary": "Minimal anxiety"},
            {"min": 5, "max": 9, "severity": "MILD", "clinical_summary": "Mild anxiety symptoms"},
            {"min": 10, "max": 14, "severity": "MODERATE", "clinical_summary": "Moderate anxiety symptoms"},
            {"min": 15, "max": 21, "severity": "SEVERE", "clinical_summary": "Severe anxiety symptoms"},
        ],
    },
    {
        "prom_id": "PROM-PROMIS10",
        "title": "PROMIS Global Health (PROMIS-10)",
        "domain": "quality_of_life",
        "version": "2026.1",
        "scoring_method": "sum_total",
        "questions_json": [
            {
                "id": "1",
                "prompt": "In general, would you say your health is:",
                "options": [
                    {"label": "Poor", "score": 1},
                    {"label": "Fair", "score": 2},
                    {"label": "Good", "score": 3},
                    {"label": "Very good", "score": 4},
                    {"label": "Excellent", "score": 5},
                ],
            },
            {
                "id": "2",
                "prompt": "In general, would you say your quality of life is:",
                "options": [
                    {"label": "Poor", "score": 1},
                    {"label": "Fair", "score": 2},
                    {"label": "Good", "score": 3},
                    {"label": "Very good", "score": 4},
                    {"label": "Excellent", "score": 5},
                ],
            },
            {
                "id": "3",
                "prompt": "In general, how would you rate your physical health?",
                "options": [
                    {"label": "Poor", "score": 1},
                    {"label": "Fair", "score": 2},
                    {"label": "Good", "score": 3},
                    {"label": "Very good", "score": 4},
                    {"label": "Excellent", "score": 5},
                ],
            },
            {
                "id": "4",
                "prompt": "In general, how would you rate your mental health?",
                "options": [
                    {"label": "Poor", "score": 1},
                    {"label": "Fair", "score": 2},
                    {"label": "Good", "score": 3},
                    {"label": "Very good", "score": 4},
                    {"label": "Excellent", "score": 5},
                ],
            },
        ],
        "interpretation_ranges_json": [
            {"min": 4, "max": 8, "severity": "POOR", "clinical_summary": "Poor overall health and functional burden"},
            {"min": 9, "max": 14, "severity": "FAIR", "clinical_summary": "Fair global health status"},
            {"min": 15, "max": 20, "severity": "GOOD_EXCELLENT", "clinical_summary": "Good to excellent functional health"},
        ],
    },
]


def seed_default_prom_definitions(db: Session) -> list[PROMDefinition]:
    """Seed baseline standard PROM definitions if missing."""
    seeded = []
    for prom_data in DEFAULT_PROMS:
        stmt = select(PROMDefinition).where(PROMDefinition.prom_id == prom_data["prom_id"])
        existing = db.execute(stmt).scalar_one_or_none()
        if not existing:
            new_prom = PROMDefinition(
                prom_id=prom_data["prom_id"],
                title=prom_data["title"],
                domain=prom_data["domain"],
                version=prom_data["version"],
                scoring_method=prom_data["scoring_method"],
                questions_json=prom_data["questions_json"],
                interpretation_ranges_json=prom_data["interpretation_ranges_json"],
                is_active=True,
            )
            db.add(new_prom)
            seeded.append(new_prom)
    if seeded:
        db.commit()
        for p in seeded:
            db.refresh(p)
    return seeded


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_patient_by_id_or_identifier(db: Session, identifier: str) -> Patient:
    """Resolve patient by database ID or patient_id string."""
    stmt = select(Patient).where(Patient.patient_id == identifier)
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient and identifier.isdigit():
        patient = db.get(Patient, int(identifier))
    if not patient:
        raise ValueError(f"Patient '{identifier}' was not found.")
    return patient


def _ensure_active_care_plan(db: Session, patient_id: int, user_id: int) -> CarePlan:
    """Retrieve active care plan or create default RPM CarePlan for the patient."""
    stmt = (
        select(CarePlan)
        .where(CarePlan.patient_id == patient_id, CarePlan.status == CarePlanStatus.ACTIVE)
        .order_by(desc(CarePlan.created_at))
    )
    plan = db.execute(stmt).scalars().first()
    if not plan:
        plan_id = f"CP-RPM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        plan = CarePlan(
            plan_id=plan_id,
            patient_id=patient_id,
            author_user_id=user_id,
            title="Remote Patient Monitoring (RPM) Care Protocol",
            description="Comprehensive out-of-hospital telemetry and remote patient monitoring protocol.",
            category=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT,
            status=CarePlanStatus.ACTIVE,
            start_date=datetime.now(timezone.utc),
        )

        db.add(plan)
        db.flush()
    return plan


# ==============================================================================
# RPM PROGRAMS & DEVICES
# ==============================================================================

def enroll_patient_in_rpm(
    db: Session, current_user: User, data: RPMProgramEnrollRequest
) -> RPMProgramResponse:
    """Enroll a patient into a clinical remote monitoring protocol."""
    patient = _get_patient_by_id_or_identifier(db, data.patient_id)
    program_id = f"RPM-PROG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    program = RPMProgram(
        program_id=program_id,
        patient_id=patient.id,
        enrolled_by_user_id=current_user.id,
        condition_name=data.condition_name,
        program_name=data.program_name,
        status="active",
        target_cadence_days=data.target_cadence_days,
        clinical_goals_json=data.clinical_goals,
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    logger.info("Enrolled patient_id=%s into RPM program_id=%s", patient.patient_id, program.program_id)
    return RPMProgramResponse(
        id=program.id,
        program_id=program.program_id,
        patient_id=program.patient_id,
        patient_identifier=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        enrolled_by_user_id=program.enrolled_by_user_id,
        condition_name=program.condition_name,
        program_name=program.program_name,
        status=program.status,
        target_cadence_days=program.target_cadence_days,
        clinical_goals_json=program.clinical_goals_json,
        discharged_at=program.discharged_at,
        discharge_reason=program.discharge_reason,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


def list_rpm_programs(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RPMProgramResponse], int]:
    """List RPM programs with patient isolation."""
    stmt = select(RPMProgram).join(Patient, RPMProgram.patient_id == Patient.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(RPMProgram.patient_id == patient.id)

    if status:
        stmt = stmt.where(RPMProgram.status == status)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(RPMProgram.created_at)).offset(skip).limit(limit)
    programs = db.execute(stmt).scalars().all()

    items = [
        RPMProgramResponse(
            id=p.id,
            program_id=p.program_id,
            patient_id=p.patient_id,
            patient_identifier=p.patient.patient_id if p.patient else None,
            patient_name=f"{p.patient.first_name} {p.patient.last_name}" if p.patient else None,
            enrolled_by_user_id=p.enrolled_by_user_id,
            condition_name=p.condition_name,
            program_name=p.program_name,
            status=p.status,
            target_cadence_days=p.target_cadence_days,
            clinical_goals_json=p.clinical_goals_json,
            discharged_at=p.discharged_at,
            discharge_reason=p.discharge_reason,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in programs
    ]
    return items, total


def register_device(
    db: Session, current_user: User, data: RPMDeviceCreate
) -> RPMDeviceResponse:
    """Register and assign a connected medical device."""
    patient = None
    if data.patient_id:
        patient = _get_patient_by_id_or_identifier(db, data.patient_id)

    device_id = data.device_id or f"DEV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    device = RPMDevice(
        device_id=device_id,
        patient_id=patient.id if patient else None,
        device_type=data.device_type.value,
        manufacturer=data.manufacturer,
        model_number=data.model_number,
        serial_number=data.serial_number,
        status="active",
        supported_measurements_json=data.supported_measurements,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    logger.info("Registered RPM device_id=%s for patient_id=%s", device.device_id, patient.patient_id if patient else None)
    return RPMDeviceResponse(
        id=device.id,
        device_id=device.device_id,
        patient_id=device.patient_id,
        patient_identifier=patient.patient_id if patient else None,
        patient_name=f"{patient.first_name} {patient.last_name}" if patient else None,
        device_type=device.device_type,
        manufacturer=device.manufacturer,
        model_number=device.model_number,
        serial_number=device.serial_number,
        status=device.status,
        supported_measurements_json=device.supported_measurements_json,
        last_sync_at=device.last_sync_at,
        created_at=device.created_at,
    )


def list_devices(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    device_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RPMDeviceResponse], int]:
    """List registered RPM devices with patient isolation."""
    stmt = select(RPMDevice).outerjoin(Patient, RPMDevice.patient_id == Patient.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(RPMDevice.patient_id == patient.id)

    if device_type:
        stmt = stmt.where(RPMDevice.device_type == device_type)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(RPMDevice.created_at)).offset(skip).limit(limit)
    devices = db.execute(stmt).scalars().all()

    items = [
        RPMDeviceResponse(
            id=d.id,
            device_id=d.device_id,
            patient_id=d.patient_id,
            patient_identifier=d.patient.patient_id if d.patient else None,
            patient_name=f"{d.patient.first_name} {d.patient.last_name}" if d.patient else None,
            device_type=d.device_type,
            manufacturer=d.manufacturer,
            model_number=d.model_number,
            serial_number=d.serial_number,
            status=d.status,
            supported_measurements_json=d.supported_measurements_json,
            last_sync_at=d.last_sync_at,
            created_at=d.created_at,
        )
        for d in devices
    ]
    return items, total


# ==============================================================================
# OBSERVATION INGESTION & THRESHOLD EVALUATION
# ==============================================================================

def ingest_observation(
    db: Session, current_user: User, data: RPMObservationCreate
) -> RPMObservationResponse:
    """Ingest a physiological telemetry observation, evaluate thresholds, and trigger escalations."""
    patient = _get_patient_by_id_or_identifier(db, data.patient_id)
    if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
        raise PermissionError("Patients can only ingest observations for their own profile.")

    device = None
    if data.device_id:
        stmt = select(RPMDevice).where(RPMDevice.device_id == data.device_id)
        device = db.execute(stmt).scalar_one_or_none()
        if device:
            device.last_sync_at = datetime.now(timezone.utc)

    # Fetch custom threshold rule for patient & observation_type if available
    stmt_rule = (
        select(RPMThresholdRule)
        .where(
            RPMThresholdRule.observation_type == data.observation_type,
            RPMThresholdRule.is_active == True,
            (RPMThresholdRule.patient_id == patient.id) | (RPMThresholdRule.patient_id == None),
        )
        .order_by(desc(RPMThresholdRule.patient_id))
    )
    custom_rule = db.execute(stmt_rule).scalars().first()

    # Deterministic Evaluation
    classification, reason = rpm_provider.evaluate_observation(
        observation_type=data.observation_type,
        numeric_value=data.numeric_value,
        secondary_value=data.secondary_value,
        custom_rule=custom_rule,
    )

    observation_id = f"ROBS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    measured_time = data.measured_at or datetime.now(timezone.utc)

    observation = RPMObservation(
        observation_id=observation_id,
        patient_id=patient.id,
        device_id=device.id if device else None,
        observation_type=data.observation_type,
        numeric_value=data.numeric_value,
        secondary_value=data.secondary_value,
        unit_of_measure=data.unit_of_measure,
        classification=classification,
        source_type=data.source_type,
        measured_at=measured_time,
        is_acknowledged=False,
        raw_payload_json=data.raw_payload,
    )
    db.add(observation)
    db.flush()

    # Check for consecutive repeated abnormal readings
    if classification == ObservationClassification.ABNORMAL.value:
        consecutive_target = custom_rule.consecutive_readings_trigger if custom_rule else 2
        recent_stmt = (
            select(RPMObservation)
            .where(
                RPMObservation.patient_id == patient.id,
                RPMObservation.observation_type == data.observation_type,
                RPMObservation.id != observation.id,
            )
            .order_by(desc(RPMObservation.measured_at))
            .limit(consecutive_target - 1)
        )
        previous_obs = db.execute(recent_stmt).scalars().all()
        if len(previous_obs) == consecutive_target - 1 and all(
            p.classification in ["abnormal", "critical"] for p in previous_obs
        ):
            classification = ObservationClassification.CRITICAL.value
            reason = f"Repeated Out-of-Range Telemetry: {consecutive_target} consecutive abnormal {data.observation_type} measurements."

    # Automated Escalation Handling for Critical Out-of-Range Telemetry
    if classification == ObservationClassification.CRITICAL.value:
        escalation_id = f"RESC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        alert_reason = reason or f"Critical out-of-range {data.observation_type} observation ({data.numeric_value} {data.unit_of_measure})."

        # 1. Attach urgent CareTask to active CarePlan
        care_plan = _ensure_active_care_plan(db, patient.id, current_user.id)
        task_id_str = f"TSK-RPM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        care_task = CareTask(
            task_id=task_id_str,
            care_plan_id=care_plan.id,
            patient_id=patient.id,
            title=f"URGENT RPM Escalation: Review {data.observation_type}",
            instructions=f"Urgent clinical evaluation required: {alert_reason}. Contact patient and assess clinical symptoms.",
            task_type=CareTaskType.GENERAL_TASK,
            priority=TaskPriority.URGENT,
            status=CareTaskStatus.PENDING,
            due_date=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(care_task)
        db.flush()

        # 2. Record RPMEscalationAlert
        rpm_alert = RPMEscalationAlert(
            alert_id=escalation_id,
            patient_id=patient.id,
            observation_id=observation.id,
            severity="CRITICAL",
            status="open",
            escalation_reason=alert_reason,
            linked_care_task_id=care_task.id,
        )
        db.add(rpm_alert)

        # 3. Create CDS Alert
        cds_alert_id = f"ALT-RPM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        cds_alert = ClinicalAlert(
            alert_id=cds_alert_id,
            patient_id=patient.id,
            alert_type="rpm_critical_threshold",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            title=f"Critical RPM Telemetry: {data.observation_type}",
            explanation=f"{alert_reason}. Recommendation: Review urgent RPM alert and adjust patient pharmacotherapy/management protocol.",
        )
        db.add(cds_alert)


    db.commit()
    db.refresh(observation)

    logger.info("Ingested RPM observation_id=%s class=%s for patient_id=%s", observation.observation_id, observation.classification, patient.patient_id)
    return RPMObservationResponse(
        id=observation.id,
        observation_id=observation.observation_id,
        patient_id=observation.patient_id,
        patient_identifier=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        device_id=observation.device_id,
        device_identifier=device.device_id if device else None,
        observation_type=observation.observation_type,
        numeric_value=observation.numeric_value,
        secondary_value=observation.secondary_value,
        unit_of_measure=observation.unit_of_measure,
        classification=observation.classification,
        source_type=observation.source_type,
        measured_at=observation.measured_at,
        ingested_at=observation.ingested_at,
        is_acknowledged=observation.is_acknowledged,
        raw_payload_json=observation.raw_payload_json,
    )


def list_observations(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    observation_type: Optional[str] = None,
    classification: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RPMObservationResponse], int]:
    """List RPM observations with strict RBAC patient isolation."""
    stmt = select(RPMObservation).join(Patient, RPMObservation.patient_id == Patient.id).outerjoin(RPMDevice, RPMObservation.device_id == RPMDevice.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(RPMObservation.patient_id == patient.id)

    if observation_type:
        stmt = stmt.where(RPMObservation.observation_type == observation_type)
    if classification:
        stmt = stmt.where(RPMObservation.classification == classification)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(RPMObservation.measured_at)).offset(skip).limit(limit)
    observations = db.execute(stmt).scalars().all()

    items = [
        RPMObservationResponse(
            id=o.id,
            observation_id=o.observation_id,
            patient_id=o.patient_id,
            patient_identifier=o.patient.patient_id if o.patient else None,
            patient_name=f"{o.patient.first_name} {o.patient.last_name}" if o.patient else None,
            device_id=o.device_id,
            device_identifier=o.device.device_id if o.device else None,
            observation_type=o.observation_type,
            numeric_value=o.numeric_value,
            secondary_value=o.secondary_value,
            unit_of_measure=o.unit_of_measure,
            classification=o.classification,
            source_type=o.source_type,
            measured_at=o.measured_at,
            ingested_at=o.ingested_at,
            is_acknowledged=o.is_acknowledged,
            raw_payload_json=o.raw_payload_json,
        )
        for o in observations
    ]
    return items, total


def get_patient_telemetry_summary(
    db: Session, current_user: User, patient_id_str: str
) -> RPMTelemetrySummary:
    """Calculate aggregated RPM telemetry summary and trends for a patient."""
    patient = _get_patient_by_id_or_identifier(db, patient_id_str)
    if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
        raise PermissionError("Access denied to requested patient telemetry summary.")

    # Recent observations
    obs_stmt = (
        select(RPMObservation)
        .where(RPMObservation.patient_id == patient.id)
        .order_by(desc(RPMObservation.measured_at))
        .limit(20)
    )
    recent_obs = db.execute(obs_stmt).scalars().all()

    # Active Program
    prog_stmt = select(RPMProgram).where(RPMProgram.patient_id == patient.id, RPMProgram.status == "active").order_by(desc(RPMProgram.created_at))
    active_prog = db.execute(prog_stmt).scalars().first()

    # Critical Alerts Count
    alerts_stmt = select(func.count(RPMEscalationAlert.id)).where(RPMEscalationAlert.patient_id == patient.id, RPMEscalationAlert.status == "open")
    critical_alerts_count = db.execute(alerts_stmt).scalar() or 0

    # Averages
    def avg_for(obs_type: str) -> Optional[float]:
        vals = [o.numeric_value for o in recent_obs if o.observation_type == obs_type]
        return round(sum(vals) / len(vals), 1) if vals else None

    return RPMTelemetrySummary(
        patient_id=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        active_program_name=active_prog.program_name if active_prog else None,
        total_observations_count=len(recent_obs),
        recent_readings=[
            RPMObservationResponse(
                id=o.id,
                observation_id=o.observation_id,
                patient_id=o.patient_id,
                patient_identifier=patient.patient_id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                device_id=o.device_id,
                device_identifier=o.device.device_id if o.device else None,
                observation_type=o.observation_type,
                numeric_value=o.numeric_value,
                secondary_value=o.secondary_value,
                unit_of_measure=o.unit_of_measure,
                classification=o.classification,
                source_type=o.source_type,
                measured_at=o.measured_at,
                ingested_at=o.ingested_at,
                is_acknowledged=o.is_acknowledged,
                raw_payload_json=o.raw_payload_json,
            )
            for o in recent_obs
        ],
        critical_alerts_count=critical_alerts_count,
        average_systolic_bp=avg_for("systolic_bp"),
        average_diastolic_bp=avg_for("diastolic_bp"),
        average_heart_rate=avg_for("heart_rate"),
        average_spo2=avg_for("spo2_percent"),
        average_glucose=avg_for("glucose_mgdl"),
    )


# ==============================================================================
# ESCALATION ALERTS
# ==============================================================================

def list_escalation_alerts(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RPMEscalationAlertResponse], int]:
    """List RPM escalation alerts with patient isolation."""
    stmt = select(RPMEscalationAlert).join(Patient, RPMEscalationAlert.patient_id == Patient.id).outerjoin(RPMObservation, RPMEscalationAlert.observation_id == RPMObservation.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(RPMEscalationAlert.patient_id == patient.id)

    if status:
        stmt = stmt.where(RPMEscalationAlert.status == status)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(RPMEscalationAlert.created_at)).offset(skip).limit(limit)
    alerts = db.execute(stmt).scalars().all()

    items = [
        RPMEscalationAlertResponse(
            id=a.id,
            alert_id=a.alert_id,
            patient_id=a.patient_id,
            patient_identifier=a.patient.patient_id if a.patient else None,
            patient_name=f"{a.patient.first_name} {a.patient.last_name}" if a.patient else None,
            observation_id=a.observation_id,
            observation_identifier=a.observation.observation_id if a.observation else None,
            severity=a.severity,
            status=a.status,
            escalation_reason=a.escalation_reason,
            clinical_action_taken=a.clinical_action_taken,
            linked_care_task_id=a.linked_care_task_id,
            acknowledged_by_user_id=a.acknowledged_by_user_id,
            resolved_by_user_id=a.resolved_by_user_id,
            created_at=a.created_at,
            acknowledged_at=a.acknowledged_at,
            resolved_at=a.resolved_at,
        )
        for a in alerts
    ]
    return items, total


def acknowledge_escalation_alert(
    db: Session, current_user: User, alert_id_str: str, data: RPMEscalationAcknowledgeRequest
) -> RPMEscalationAlertResponse:
    """Acknowledge an RPM escalation alert."""
    stmt = select(RPMEscalationAlert).where(RPMEscalationAlert.alert_id == alert_id_str)
    alert = db.execute(stmt).scalar_one_or_none()
    if not alert:
        raise ValueError(f"RPM escalation alert '{alert_id_str}' was not found.")

    alert.status = "acknowledged"
    alert.acknowledged_by_user_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    if data.notes:
        alert.clinical_action_taken = data.notes

    db.commit()
    db.refresh(alert)

    logger.info("Acknowledged RPM alert_id=%s by user_id=%s", alert.alert_id, current_user.id)
    return RPMEscalationAlertResponse(
        id=alert.id,
        alert_id=alert.alert_id,
        patient_id=alert.patient_id,
        patient_identifier=alert.patient.patient_id if alert.patient else None,
        patient_name=f"{alert.patient.first_name} {alert.patient.last_name}" if alert.patient else None,
        observation_id=alert.observation_id,
        observation_identifier=alert.observation.observation_id if alert.observation else None,
        severity=alert.severity,
        status=alert.status,
        escalation_reason=alert.escalation_reason,
        clinical_action_taken=alert.clinical_action_taken,
        linked_care_task_id=alert.linked_care_task_id,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
        resolved_by_user_id=alert.resolved_by_user_id,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
    )


def resolve_escalation_alert(
    db: Session, current_user: User, alert_id_str: str, data: RPMEscalationResolveRequest
) -> RPMEscalationAlertResponse:
    """Resolve an RPM escalation alert with documented clinical remediation."""
    stmt = select(RPMEscalationAlert).where(RPMEscalationAlert.alert_id == alert_id_str)
    alert = db.execute(stmt).scalar_one_or_none()
    if not alert:
        raise ValueError(f"RPM escalation alert '{alert_id_str}' was not found.")

    alert.status = "resolved"
    alert.resolved_by_user_id = current_user.id
    alert.resolved_at = datetime.now(timezone.utc)
    alert.clinical_action_taken = data.clinical_action_taken

    if alert.linked_care_task_id and data.create_care_task:
        task = db.get(CareTask, alert.linked_care_task_id)
        if task:
            task.status = CareTaskStatus.COMPLETED

    db.commit()
    db.refresh(alert)

    logger.info("Resolved RPM alert_id=%s by user_id=%s", alert.alert_id, current_user.id)
    return RPMEscalationAlertResponse(
        id=alert.id,
        alert_id=alert.alert_id,
        patient_id=alert.patient_id,
        patient_identifier=alert.patient.patient_id if alert.patient else None,
        patient_name=f"{alert.patient.first_name} {alert.patient.last_name}" if alert.patient else None,
        observation_id=alert.observation_id,
        observation_identifier=alert.observation.observation_id if alert.observation else None,
        severity=alert.severity,
        status=alert.status,
        escalation_reason=alert.escalation_reason,
        clinical_action_taken=alert.clinical_action_taken,
        linked_care_task_id=alert.linked_care_task_id,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
        resolved_by_user_id=alert.resolved_by_user_id,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
    )


# ==============================================================================
# PATIENT-REPORTED OUTCOMES (PROMS)
# ==============================================================================

def list_prom_definitions(db: Session, domain: Optional[str] = None) -> list[PROMDefinitionResponse]:
    """List available standardized PROM questionnaire templates."""
    seed_default_prom_definitions(db)
    stmt = select(PROMDefinition).where(PROMDefinition.is_active == True)
    if domain:
        stmt = stmt.where(PROMDefinition.domain == domain)
    proms = db.execute(stmt).scalars().all()
    return [
        PROMDefinitionResponse(
            id=p.id,
            prom_id=p.prom_id,
            title=p.title,
            domain=p.domain,
            version=p.version,
            questions_json=p.questions_json,
            scoring_method=p.scoring_method,
            interpretation_ranges_json=p.interpretation_ranges_json,
            is_active=p.is_active,
            created_at=p.created_at,
        )
        for p in proms
    ]


def submit_prom_response(
    db: Session, current_user: User, data: PROMResponseSubmitRequest
) -> PROMResponseDetail:
    """Submit patient PROM response with deterministic multi-domain scoring."""
    patient = _get_patient_by_id_or_identifier(db, data.patient_id)
    if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
        raise PermissionError("Patients can only submit PROM questionnaires for themselves.")

    stmt = select(PROMDefinition).where(PROMDefinition.prom_id == data.prom_id)
    prom_def = db.execute(stmt).scalar_one_or_none()
    if not prom_def:
        raise ValueError(f"PROM questionnaire '{data.prom_id}' was not found.")

    # Score PROM
    score, interpretation, safety_flags = rpm_provider.score_prom(
        questions=prom_def.questions_json,
        scoring_method=prom_def.scoring_method,
        interpretation_ranges=prom_def.interpretation_ranges_json,
        answers=data.answers,
    )

    response_id = f"PRES-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    prom_response = PROMResponse(
        response_id=response_id,
        prom_id=prom_def.id,
        patient_id=patient.id,
        encounter_id=int(data.encounter_id) if data.encounter_id and data.encounter_id.isdigit() else None,
        answers_json=data.answers,
        calculated_score=score,
        severity_interpretation=interpretation,
        clinical_notes=data.clinical_notes,
    )
    db.add(prom_response)

    # Handle safety flags (e.g. Suicidal Ideation in PHQ-9 Q9)
    if safety_flags:
        alert_id = f"ALT-PROM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        alert_desc = f"Critical safety flag identified in {prom_def.title} assessment: {'; '.join(safety_flags)}"
        cds_alert = ClinicalAlert(
            alert_id=alert_id,
            patient_id=patient.id,
            alert_type="prom_safety_flag",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            title=f"Critical PROM Assessment Flag: {prom_def.prom_id}",
            explanation=f"{alert_desc}. Recommendation: Immediate behavioral health clinician contact and safety protocol activation.",
        )
        db.add(cds_alert)


    db.commit()
    db.refresh(prom_response)

    logger.info("Submitted PROM response_id=%s for patient_id=%s score=%s", prom_response.response_id, patient.patient_id, score)
    return PROMResponseDetail(
        id=prom_response.id,
        response_id=prom_response.response_id,
        prom_id=prom_response.prom_id,
        prom_code=prom_def.prom_id,
        prom_title=prom_def.title,
        patient_id=prom_response.patient_id,
        patient_identifier=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        encounter_id=prom_response.encounter_id,
        answers_json=prom_response.answers_json,
        calculated_score=prom_response.calculated_score,
        severity_interpretation=prom_response.severity_interpretation,
        clinical_notes=prom_response.clinical_notes,
        completed_at=prom_response.completed_at,
        reviewed_by_user_id=prom_response.reviewed_by_user_id,
        reviewed_at=prom_response.reviewed_at,
    )


def list_prom_responses(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    prom_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[PROMResponseDetail], int]:
    """List historical PROM submissions with patient isolation."""
    stmt = select(PROMResponse).join(Patient, PROMResponse.patient_id == Patient.id).join(PROMDefinition, PROMResponse.prom_id == PROMDefinition.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(PROMResponse.patient_id == patient.id)

    if prom_id:
        stmt = stmt.where(PROMDefinition.prom_id == prom_id)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(PROMResponse.completed_at)).offset(skip).limit(limit)
    responses = db.execute(stmt).scalars().all()

    items = [
        PROMResponseDetail(
            id=r.id,
            response_id=r.response_id,
            prom_id=r.prom_id,
            prom_code=r.prom.prom_id if r.prom else None,
            prom_title=r.prom.title if r.prom else None,
            patient_id=r.patient_id,
            patient_identifier=r.patient.patient_id if r.patient else None,
            patient_name=f"{r.patient.first_name} {r.patient.last_name}" if r.patient else None,
            encounter_id=r.encounter_id,
            answers_json=r.answers_json,
            calculated_score=r.calculated_score,
            severity_interpretation=r.severity_interpretation,
            clinical_notes=r.clinical_notes,
            completed_at=r.completed_at,
            reviewed_by_user_id=r.reviewed_by_user_id,
            reviewed_at=r.reviewed_at,
        )
        for r in responses
    ]
    return items, total


# ==============================================================================
# TELEHEALTH & VIRTUAL CARE SESSIONS
# ==============================================================================

def schedule_telehealth_session(
    db: Session, current_user: User, data: TelehealthSessionCreate
) -> TelehealthSessionResponse:
    """Schedule a virtual care telehealth session and generate pre-visit clinical briefing."""
    patient = _get_patient_by_id_or_identifier(db, data.patient_id)
    clinician_id = data.clinician_user_id or current_user.id

    # Fetch recent RPM observations
    recent_obs_stmt = (
        select(RPMObservation)
        .where(RPMObservation.patient_id == patient.id)
        .order_by(desc(RPMObservation.measured_at))
        .limit(10)
    )
    recent_obs = db.execute(recent_obs_stmt).scalars().all()
    obs_dicts = [
        {
            "observation_type": o.observation_type,
            "numeric_value": o.numeric_value,
            "classification": o.classification,
            "measured_at": o.measured_at.isoformat() if o.measured_at else None,
        }
        for o in recent_obs
    ]

    # Fetch recent PROM responses
    prom_stmt = (
        select(PROMResponse)
        .where(PROMResponse.patient_id == patient.id)
        .order_by(desc(PROMResponse.completed_at))
        .limit(5)
    )
    recent_proms = db.execute(prom_stmt).scalars().all()
    prom_dicts = [
        {
            "prom_code": p.prom.prom_id if p.prom else None,
            "calculated_score": p.calculated_score,
            "severity_interpretation": p.severity_interpretation,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        }
        for p in recent_proms
    ]

    # Active programs
    prog_stmt = select(RPMProgram).where(RPMProgram.patient_id == patient.id, RPMProgram.status == "active")
    active_progs = db.execute(prog_stmt).scalars().all()
    prog_dicts = [{"condition_name": p.condition_name, "program_name": p.program_name} for p in active_progs]

    # Pre-visit clinical briefing
    pre_visit_briefing = rpm_provider.synthesize_telehealth_briefing(
        patient_identifier=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        recent_observations=obs_dicts,
        recent_prom_responses=prom_dicts,
        active_programs=prog_dicts,
    )

    session_id = f"TELE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    telehealth = TelehealthSession(
        session_id=session_id,
        patient_id=patient.id,
        clinician_user_id=clinician_id,
        appointment_id=int(data.appointment_id) if data.appointment_id and data.appointment_id.isdigit() else None,
        encounter_id=int(data.encounter_id) if data.encounter_id and data.encounter_id.isdigit() else None,
        status="scheduled",
        scheduled_start=data.scheduled_start,
        visit_reason=data.visit_reason,
        pre_visit_rpm_summary_json=pre_visit_briefing,
        pre_visit_prom_summary_json=prom_dicts[0] if prom_dicts else None,
    )
    db.add(telehealth)
    db.commit()
    db.refresh(telehealth)

    logger.info("Scheduled telehealth session_id=%s for patient_id=%s", telehealth.session_id, patient.patient_id)
    return TelehealthSessionResponse(
        id=telehealth.id,
        session_id=telehealth.session_id,
        patient_id=telehealth.patient_id,
        patient_identifier=patient.patient_id,
        patient_name=f"{patient.first_name} {patient.last_name}",
        clinician_user_id=telehealth.clinician_user_id,
        clinician_name=current_user.name or current_user.email,
        appointment_id=telehealth.appointment_id,
        encounter_id=telehealth.encounter_id,
        status=telehealth.status,
        scheduled_start=telehealth.scheduled_start,
        actual_start=telehealth.actual_start,
        actual_end=telehealth.actual_end,
        visit_reason=telehealth.visit_reason,
        pre_visit_rpm_summary_json=telehealth.pre_visit_rpm_summary_json,
        pre_visit_prom_summary_json=telehealth.pre_visit_prom_summary_json,
        session_notes=telehealth.session_notes,
        followup_instructions=telehealth.followup_instructions,
        created_at=telehealth.created_at,
        updated_at=telehealth.updated_at,
    )


def update_telehealth_session(
    db: Session, current_user: User, session_id_str: str, data: TelehealthSessionUpdate
) -> TelehealthSessionResponse:
    """Update virtual care session lifecycle, clinical notes, and post-visit tasks."""
    stmt = select(TelehealthSession).where(TelehealthSession.session_id == session_id_str)
    session = db.execute(stmt).scalar_one_or_none()
    if not session:
        raise ValueError(f"Telehealth session '{session_id_str}' was not found.")

    if data.status:
        session.status = data.status.value
        if data.status == TelehealthStatus.IN_PROGRESS and not session.actual_start:
            session.actual_start = datetime.now(timezone.utc)
        elif data.status == TelehealthStatus.COMPLETED and not session.actual_end:
            session.actual_end = datetime.now(timezone.utc)

    if data.session_notes is not None:
        session.session_notes = data.session_notes
    if data.followup_instructions is not None:
        session.followup_instructions = data.followup_instructions

    # Create post-visit follow-up task if requested
    if data.create_followup_task and data.followup_instructions:
        care_plan = _ensure_active_care_plan(db, session.patient_id, current_user.id)
        task_id_str = f"TSK-TELE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        care_task = CareTask(
            task_id=task_id_str,
            care_plan_id=care_plan.id,
            patient_id=session.patient_id,
            title="Telehealth Follow-up Action",
            instructions=data.followup_instructions,
            task_type=CareTaskType.GENERAL_TASK,
            priority=TaskPriority.ROUTINE,
            status=CareTaskStatus.PENDING,
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(care_task)

    db.commit()
    db.refresh(session)

    logger.info("Updated telehealth session_id=%s status=%s", session.session_id, session.status)
    return TelehealthSessionResponse(
        id=session.id,
        session_id=session.session_id,
        patient_id=session.patient_id,
        patient_identifier=session.patient.patient_id if session.patient else None,
        patient_name=f"{session.patient.first_name} {session.patient.last_name}" if session.patient else None,
        clinician_user_id=session.clinician_user_id,
        clinician_name=session.clinician.name or session.clinician.email if session.clinician else None,
        appointment_id=session.appointment_id,
        encounter_id=session.encounter_id,
        status=session.status,
        scheduled_start=session.scheduled_start,
        actual_start=session.actual_start,
        actual_end=session.actual_end,
        visit_reason=session.visit_reason,
        pre_visit_rpm_summary_json=session.pre_visit_rpm_summary_json,
        pre_visit_prom_summary_json=session.pre_visit_prom_summary_json,
        session_notes=session.session_notes,
        followup_instructions=session.followup_instructions,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def list_telehealth_sessions(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[TelehealthSessionResponse], int]:
    """List telehealth sessions with RBAC patient isolation."""
    stmt = select(TelehealthSession).join(Patient, TelehealthSession.patient_id == Patient.id)
    if current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.email == current_user.email)
    elif patient_id:
        patient = _get_patient_by_id_or_identifier(db, patient_id)
        stmt = stmt.where(TelehealthSession.patient_id == patient.id)

    if status:
        stmt = stmt.where(TelehealthSession.status == status)

    total = len(db.execute(stmt).scalars().all())
    stmt = stmt.order_by(desc(TelehealthSession.scheduled_start)).offset(skip).limit(limit)
    sessions = db.execute(stmt).scalars().all()

    items = [
        TelehealthSessionResponse(
            id=s.id,
            session_id=s.session_id,
            patient_id=s.patient_id,
            patient_identifier=s.patient.patient_id if s.patient else None,
            patient_name=f"{s.patient.first_name} {s.patient.last_name}" if s.patient else None,
            clinician_user_id=s.clinician_user_id,
            clinician_name=s.clinician.name or s.clinician.email if s.clinician else None,
            appointment_id=s.appointment_id,
            encounter_id=s.encounter_id,
            status=s.status,
            scheduled_start=s.scheduled_start,
            actual_start=s.actual_start,
            actual_end=s.actual_end,
            visit_reason=s.visit_reason,
            pre_visit_rpm_summary_json=s.pre_visit_rpm_summary_json,
            pre_visit_prom_summary_json=s.pre_visit_prom_summary_json,
            session_notes=s.session_notes,
            followup_instructions=s.followup_instructions,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]
    return items, total


def get_telehealth_session(
    db: Session, current_user: User, session_id_str: str
) -> TelehealthSessionResponse:
    """Retrieve full details of a virtual care telehealth session."""
    stmt = select(TelehealthSession).where(TelehealthSession.session_id == session_id_str)
    session = db.execute(stmt).scalar_one_or_none()
    if not session:
        raise ValueError(f"Telehealth session '{session_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and session.patient.email != current_user.email:
        raise PermissionError("Access denied to requested virtual session.")

    return TelehealthSessionResponse(
        id=session.id,
        session_id=session.session_id,
        patient_id=session.patient_id,
        patient_identifier=session.patient.patient_id if session.patient else None,
        patient_name=f"{session.patient.first_name} {session.patient.last_name}" if session.patient else None,
        clinician_user_id=session.clinician_user_id,
        clinician_name=session.clinician.name or session.clinician.email if session.clinician else None,
        appointment_id=session.appointment_id,
        encounter_id=session.encounter_id,
        status=session.status,
        scheduled_start=session.scheduled_start,
        actual_start=session.actual_start,
        actual_end=session.actual_end,
        visit_reason=session.visit_reason,
        pre_visit_rpm_summary_json=session.pre_visit_rpm_summary_json,
        pre_visit_prom_summary_json=session.pre_visit_prom_summary_json,
        session_notes=session.session_notes,
        followup_instructions=session.followup_instructions,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

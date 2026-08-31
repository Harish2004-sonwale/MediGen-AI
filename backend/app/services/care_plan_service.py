"""Service layer for Clinical Care Plans, Follow-Up Tasks & AI Synthesis.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.care_plan_provider import get_care_plan_provider
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.models.alert import ClinicalAlert
from app.schemas.care_plan import (
    CarePlanCategory,
    CarePlanCreate,
    CarePlanListResponse,
    CarePlanResponse,
    CarePlanReviewRequest,
    CarePlanStatus,
    CarePlanSynthesizeRequest,
    CarePlanUpdate,
)
from app.schemas.care_task import (
    CareTaskCompleteRequest,
    CareTaskCreate,
    CareTaskListResponse,
    CareTaskResponse,
    CareTaskStatus,
    CareTaskUpdate,
)
from app.schemas.task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from app.ai.task_worker import get_background_task_provider


logger = logging.getLogger("medigen.services.care_plan")


def _validate_patient_care_access(db: Session, current_user: User, patient: Patient) -> None:
    """Enforce RBAC and strict patient data isolation for care plans and tasks."""
    if current_user.role in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.email.lower() != patient.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access care plans or tasks belonging to another patient.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges to access patient care plans.",
    )


def _generate_care_plan_id() -> str:
    """Generate unique public care plan identifier (CP-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"CP-{date_str}-{unique_suffix}"


def _generate_care_task_id() -> str:
    """Generate unique public care task identifier (CTSK-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"CTSK-{date_str}-{unique_suffix}"


def _to_task_response(task: CareTask) -> CareTaskResponse:
    """Convert CareTask ORM to CareTaskResponse with computed is_overdue field."""
    due = task.due_date
    if due.tzinfo is not None:
        due = due.astimezone(timezone.utc).replace(tzinfo=None)
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    is_overdue = task.status != CareTaskStatus.COMPLETED and due < now_naive

    return CareTaskResponse(
        id=task.id,
        task_id=task.task_id,
        patient_id=task.patient_id,
        care_plan_id=task.care_plan_id,
        encounter_id=task.encounter_id,
        appointment_id=task.appointment_id,
        assigned_user_id=task.assigned_user_id,
        title=task.title,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        instructions=task.instructions,
        due_date=task.due_date,
        is_overdue=is_overdue,
        completed_at=task.completed_at,
        completion_notes=task.completion_notes,
        created_at=task.created_at,
    )


# ==============================================================================
# CARE PLAN OPERATIONS
# ==============================================================================

def create_care_plan(
    db: Session,
    patient_id: str,
    plan_in: CarePlanCreate,
    current_user: User,
) -> CarePlanResponse:
    """Create a new manual clinical care plan."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may create care plans.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    now = datetime.now(timezone.utc)
    start_date = plan_in.start_date or now

    care_plan = CarePlan(
        plan_id=_generate_care_plan_id(),
        patient_id=patient.id,
        author_user_id=current_user.id,
        encounter_id=plan_in.encounter_id,
        title=plan_in.title.strip(),
        category=plan_in.category,
        status=CarePlanStatus.DRAFT,
        intent=plan_in.intent,
        description=plan_in.description.strip(),
        goals_json=[g.model_dump(mode="json") for g in plan_in.goals] if plan_in.goals else [],
        interventions_json=[i.model_dump(mode="json") for i in plan_in.interventions] if plan_in.interventions else [],
        is_ai_generated=False,

        start_date=start_date,
        end_date=plan_in.end_date,
        created_at=now,
        updated_at=now,
    )
    db.add(care_plan)
    db.commit()
    db.refresh(care_plan)

    logger.info("Created care plan %s for patient_id=%s by user_id=%s", care_plan.plan_id, patient.id, current_user.id)
    return CarePlanResponse.model_validate(care_plan)


def get_care_plan(
    db: Session,
    plan_id: str,
    current_user: User,
) -> CarePlanResponse:
    """Retrieve details of a specific care plan."""
    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id)
    care_plan = db.execute(stmt).scalar_one_or_none()
    if not care_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan '{plan_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, care_plan.patient)
    return CarePlanResponse.model_validate(care_plan)


def list_patient_care_plans(
    db: Session,
    patient_id: str,
    current_user: User,
    status_filter: Optional[str] = None,
) -> CarePlanListResponse:
    """List care plans for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    plan_stmt = (
        select(CarePlan)
        .where(CarePlan.patient_id == patient.id)
        .order_by(CarePlan.created_at.desc())
    )
    if status_filter:
        plan_stmt = plan_stmt.where(CarePlan.status == status_filter)

    plans = db.execute(plan_stmt).scalars().all()
    return CarePlanListResponse(
        items=[CarePlanResponse.model_validate(p) for p in plans],
        total=len(plans),
    )


def update_care_plan(
    db: Session,
    plan_id: str,
    plan_in: CarePlanUpdate,
    current_user: User,
) -> CarePlanResponse:
    """Update an editable care plan (draft, reviewed, or active). Completed/cancelled plans are protected."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may update care plans.",
        )

    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id)
    care_plan = db.execute(stmt).scalar_one_or_none()
    if not care_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan '{plan_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, care_plan.patient)

    if care_plan.status in (CarePlanStatus.COMPLETED, CarePlanStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify care plan in finalized status '{care_plan.status.value}'.",
        )

    # Optimistic locking version check
    if plan_in.version is not None:
        current_version = getattr(care_plan, "version", 1) or 1
        if current_version != plan_in.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflict: Care plan '{plan_id}' has been modified by another user session. "
                    f"Current version is {current_version}, provided version is {plan_in.version}."
                ),
            )

    if plan_in.title is not None:
        care_plan.title = plan_in.title.strip()
    if plan_in.category is not None:
        care_plan.category = plan_in.category
    if plan_in.description is not None:
        care_plan.description = plan_in.description.strip()
    if plan_in.intent is not None:
        care_plan.intent = plan_in.intent.strip()
    if plan_in.goals is not None:
        care_plan.goals_json = [g.model_dump(mode="json") for g in plan_in.goals]
    if plan_in.interventions is not None:
        care_plan.interventions_json = [i.model_dump(mode="json") for i in plan_in.interventions]
    if plan_in.end_date is not None:
        care_plan.end_date = plan_in.end_date

    # Increment optimistic locking version
    care_plan.version = (getattr(care_plan, "version", 1) or 1) + 1
    care_plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(care_plan)

    logger.info("Updated care plan %s (v%d) by user_id=%s", care_plan.plan_id, care_plan.version, current_user.id)
    return CarePlanResponse.model_validate(care_plan)


def review_care_plan(
    db: Session,
    plan_id: str,
    review_in: CarePlanReviewRequest,
    current_user: User,
) -> CarePlanResponse:
    """Attending physician review, signoff, and activation."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only attending physicians or administrators may sign off and activate care plans.",
        )

    if not review_in.confirm_accuracy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Physician must explicitly confirm clinical accuracy before signoff.",
        )

    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id)
    care_plan = db.execute(stmt).scalar_one_or_none()
    if not care_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan '{plan_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, care_plan.patient)

    now = datetime.now(timezone.utc)
    care_plan.reviewed_by_user_id = current_user.id
    care_plan.reviewed_at = now
    care_plan.status = CarePlanStatus.ACTIVE if review_in.activate_immediately else CarePlanStatus.REVIEWED
    care_plan.updated_at = now

    if review_in.clinician_notes:
        care_plan.description += f"\n\n[PHYSICIAN SIGNOFF NOTES]: {review_in.clinician_notes.strip()}"

    db.commit()
    db.refresh(care_plan)

    logger.info("Physician user_id=%s reviewed care plan %s (status=%s)", current_user.id, care_plan.plan_id, care_plan.status.value)
    return CarePlanResponse.model_validate(care_plan)


def complete_care_plan(
    db: Session,
    plan_id: str,
    current_user: User,
) -> CarePlanResponse:
    """Mark an active care plan as completed."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to complete care plans.",
        )

    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id)
    care_plan = db.execute(stmt).scalar_one_or_none()
    if not care_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan '{plan_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, care_plan.patient)

    care_plan.status = CarePlanStatus.COMPLETED
    care_plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(care_plan)

    logger.info("Care plan %s marked completed by user_id=%s", care_plan.plan_id, current_user.id)
    return CarePlanResponse.model_validate(care_plan)


def cancel_care_plan(
    db: Session,
    plan_id: str,
    current_user: User,
) -> CarePlanResponse:
    """Cancel or suspend a care plan."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors or administrators may cancel care plans.",
        )

    stmt = select(CarePlan).where(CarePlan.plan_id == plan_id)
    care_plan = db.execute(stmt).scalar_one_or_none()
    if not care_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care plan '{plan_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, care_plan.patient)

    care_plan.status = CarePlanStatus.CANCELLED
    care_plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(care_plan)

    logger.info("Care plan %s cancelled by user_id=%s", care_plan.plan_id, current_user.id)
    return CarePlanResponse.model_validate(care_plan)


# ==============================================================================
# AI CARE PLAN SYNTHESIS
# ==============================================================================

def synthesize_care_plan_draft(
    db: Session,
    patient_id: str,
    synth_in: CarePlanSynthesizeRequest,
    current_user: User,
) -> tuple[CarePlanResponse, list[CareTaskResponse]]:
    """Synthesize assistive draft care plan and follow-up tasks using patient longitudinal context."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may trigger AI care plan synthesis.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    # Collect patient summary context
    latest_vital = (
        db.execute(
            select(VitalTelemetry)
            .where(VitalTelemetry.patient_id == patient.id)
            .order_by(VitalTelemetry.measured_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    alerts = (
        db.execute(
            select(ClinicalAlert)
            .where(ClinicalAlert.patient_id == patient.id, ClinicalAlert.status == "active")
            .limit(5)
        )
        .scalars()
        .all()
    )

    patient_summary = {
        "name": f"{patient.first_name} {patient.last_name}",
        "conditions": [patient.medical_history] if getattr(patient, "medical_history", None) else [],
        "medications": [patient.current_medications] if getattr(patient, "current_medications", None) else [],
        "latest_vitals": {
            "spo2": latest_vital.spo2_percent if latest_vital else None,
            "hr": latest_vital.heart_rate if latest_vital else None,
            "bp": f"{latest_vital.systolic_bp}/{latest_vital.diastolic_bp}" if latest_vital and latest_vital.systolic_bp else None,
        },
        "alerts": [a.title for a in alerts],
    }

    provider = get_care_plan_provider()
    synth_output = provider.synthesize_care_plan(
        patient_summary=patient_summary,
        category=synth_in.category,
        custom_instructions=synth_in.custom_instructions,
    )

    now = datetime.now(timezone.utc)
    care_plan = CarePlan(
        plan_id=_generate_care_plan_id(),
        patient_id=patient.id,
        author_user_id=current_user.id,
        title=synth_output["title"],
        category=synth_output["category"],
        status=CarePlanStatus.DRAFT,  # AI plans MUST start in DRAFT
        intent="plan",
        description=synth_output["description"],
        goals_json=synth_output["goals"],
        interventions_json=synth_output["interventions"],
        is_ai_generated=True,
        start_date=synth_output["start_date"],
        end_date=synth_output["end_date"],
        created_at=now,
        updated_at=now,
    )
    db.add(care_plan)
    db.commit()
    db.refresh(care_plan)

    created_tasks: list[CareTask] = []
    for t in synth_output.get("suggested_tasks", []):
        task = CareTask(
            task_id=_generate_care_task_id(),
            patient_id=patient.id,
            care_plan_id=care_plan.id,
            assigned_user_id=current_user.id,
            title=t["title"],
            task_type=t["task_type"],
            priority=t["priority"],
            status=CareTaskStatus.PENDING,
            instructions=t.get("instructions"),
            due_date=t["due_date"],
            created_at=now,
        )
        db.add(task)
        created_tasks.append(task)

    db.commit()
    for task in created_tasks:
        db.refresh(task)

    logger.info("AI synthesized care plan %s with %s tasks for patient_id=%s", care_plan.plan_id, len(created_tasks), patient.id)
    return (
        CarePlanResponse.model_validate(care_plan),
        [_to_task_response(t) for t in created_tasks],
    )


# ==============================================================================
# CARE TASK OPERATIONS
# ==============================================================================

def create_care_task(
    db: Session,
    patient_id: str,
    task_in: CareTaskCreate,
    current_user: User,
) -> CareTaskResponse:
    """Create a new clinical follow-up task."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may create care tasks.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    task = CareTask(
        task_id=_generate_care_task_id(),
        patient_id=patient.id,
        care_plan_id=task_in.care_plan_id,
        encounter_id=task_in.encounter_id,
        appointment_id=task_in.appointment_id,
        assigned_user_id=task_in.assigned_user_id or current_user.id,
        title=task_in.title.strip(),
        task_type=task_in.task_type,
        priority=task_in.priority,
        status=CareTaskStatus.PENDING,
        instructions=task_in.instructions.strip() if task_in.instructions else None,
        due_date=task_in.due_date,
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info("Created care task %s for patient_id=%s", task.task_id, patient.id)
    return _to_task_response(task)


def get_care_task(
    db: Session,
    task_id: str,
    current_user: User,
) -> CareTaskResponse:
    """Retrieve details of a specific care task."""
    stmt = select(CareTask).where(CareTask.task_id == task_id)
    task = db.execute(stmt).scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, task.patient)
    return _to_task_response(task)


def list_patient_care_tasks(
    db: Session,
    patient_id: str,
    current_user: User,
    care_plan_id: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> CareTaskListResponse:
    """List follow-up tasks for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    task_stmt = (
        select(CareTask)
        .where(CareTask.patient_id == patient.id)
        .order_by(CareTask.due_date.asc())
    )
    if care_plan_id:
        if care_plan_id.isdigit():
            task_stmt = task_stmt.where(CareTask.care_plan_id == int(care_plan_id))
        else:
            plan_sub = select(CarePlan.id).where(CarePlan.plan_id == care_plan_id).scalar_subquery()
            task_stmt = task_stmt.where(CareTask.care_plan_id == plan_sub)

    if status_filter:
        task_stmt = task_stmt.where(CareTask.status == status_filter)

    tasks = db.execute(task_stmt).scalars().all()
    return CareTaskListResponse(
        items=[_to_task_response(t) for t in tasks],
        total=len(tasks),
    )


def update_care_task(
    db: Session,
    task_id: str,
    task_in: CareTaskUpdate,
    current_user: User,
) -> CareTaskResponse:
    """Update a care task."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may update care tasks.",
        )

    stmt = select(CareTask).where(CareTask.task_id == task_id)
    task = db.execute(stmt).scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, task.patient)

    if task_in.title is not None:
        task.title = task_in.title.strip()
    if task_in.task_type is not None:
        task.task_type = task_in.task_type
    if task_in.priority is not None:
        task.priority = task_in.priority
    if task_in.instructions is not None:
        task.instructions = task_in.instructions.strip()
    if task_in.due_date is not None:
        task.due_date = task_in.due_date
    if task_in.assigned_user_id is not None:
        task.assigned_user_id = task_in.assigned_user_id
    if task_in.status is not None:
        task.status = task_in.status
        if task_in.status == CareTaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(task)

    logger.info("Updated care task %s by user_id=%s", task.task_id, current_user.id)
    return _to_task_response(task)


def complete_care_task(
    db: Session,
    task_id: str,
    complete_in: CareTaskCompleteRequest,
    current_user: User,
) -> CareTaskResponse:
    """Mark a clinical follow-up task as complete with outcome notes."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may complete care tasks.",
        )

    stmt = select(CareTask).where(CareTask.task_id == task_id)
    task = db.execute(stmt).scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Care task '{task_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, task.patient)

    task.status = CareTaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    if complete_in.completion_notes:
        task.completion_notes = complete_in.completion_notes.strip()

    db.commit()
    db.refresh(task)

    logger.info("Completed care task %s by user_id=%s", task.task_id, current_user.id)
    return _to_task_response(task)


# ==============================================================================
# ASYNC WORKER TASK
# ==============================================================================

from app.database.session import SessionLocal


def execute_care_plan_synthesis_job(
    patient_id: str,
    category: str,
    custom_instructions: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """Background worker job execution entrypoint for asynchronous care plan synthesis."""
    db = SessionLocal()
    try:
        user = None
        if user_id:
            user = db.get(User, user_id)
        if not user:
            user = User(id=1, email="system@medigen.internal", role=UserRole.ADMIN, name="System Worker")

        req = CarePlanSynthesizeRequest(
            category=CarePlanCategory(category),
            custom_instructions=custom_instructions,
        )
        plan_res, tasks_res = synthesize_care_plan_draft(
            db=db,
            patient_id=patient_id,
            synth_in=req,
            current_user=user,
        )
        return {
            "plan_id": plan_res.plan_id,
            "patient_id": str(plan_res.patient_id),
            "title": plan_res.title,
            "status": plan_res.status.value if hasattr(plan_res.status, "value") else str(plan_res.status),
            "tasks_count": len(tasks_res),
        }
    finally:
        db.close()


def enqueue_care_plan_synthesis(
    db: Session,
    patient_id: str,
    synth_in: CarePlanSynthesizeRequest,
    current_user: User,
) -> BackgroundTask:
    """Enqueue asynchronous AI care plan synthesis background task."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may trigger care plan synthesis.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    _validate_patient_care_access(db, current_user, patient)

    provider = get_background_task_provider()
    task = provider.submit_task(
        task_type=BackgroundTaskType.CARE_PLAN_GENERATION,
        fn=execute_care_plan_synthesis_job,
        fn_kwargs={
            "patient_id": patient.patient_id,
            "category": synth_in.category.value,
            "custom_instructions": synth_in.custom_instructions,
            "user_id": current_user.id,
        },
        patient_id=patient.patient_id,
        created_by_user_id=current_user.id,
        payload={
            "patient_id": patient.patient_id,
            "category": synth_in.category.value,
            "custom_instructions": synth_in.custom_instructions,
            "author_user_id": current_user.id,
        },
    )
    return task

"""API endpoints for Clinical Workflow Orchestration, Care Plans & Follow-Up Tasks.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.care_plan import (
    CarePlanCreate,
    CarePlanListResponse,
    CarePlanResponse,
    CarePlanReviewRequest,
    CarePlanSynthesizeRequest,
    CarePlanUpdate,
)
from app.schemas.care_task import (
    CareTaskCompleteRequest,
    CareTaskCreate,
    CareTaskListResponse,
    CareTaskResponse,
    CareTaskUpdate,
)
from app.schemas.task import BackgroundTaskResponse
from app.services.care_plan_service import (
    cancel_care_plan,
    complete_care_plan,
    complete_care_task,
    create_care_plan,
    create_care_task,
    enqueue_care_plan_synthesis,
    get_care_plan,
    get_care_task,
    list_patient_care_plans,
    list_patient_care_tasks,
    review_care_plan,
    update_care_plan,
    update_care_task,
)

router = APIRouter(tags=["Clinical Workflow & Care Plans"])


# ==============================================================================
# CARE PLANS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/care-plans",
    response_model=CarePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new structured clinical care plan",
)
def create_care_plan_endpoint(
    patient_id: str,
    plan_in: CarePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CarePlanResponse:
    """Create a new manual clinical care plan."""
    return create_care_plan(
        db=db,
        patient_id=patient_id,
        plan_in=plan_in,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/care-plans",
    response_model=CarePlanListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical care plans for a patient",
)
def list_patient_care_plans_endpoint(
    patient_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (draft, active, completed, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CarePlanListResponse:
    """List care plans for a patient."""
    return list_patient_care_plans(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        status_filter=status_filter,
    )


@router.get(
    "/care-plans/{care_plan_id}",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve details of a specific care plan",
)
def get_care_plan_endpoint(
    care_plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CarePlanResponse:
    """Retrieve details of a care plan."""
    return get_care_plan(
        db=db,
        plan_id=care_plan_id,
        current_user=current_user,
    )


@router.patch(
    "/care-plans/{care_plan_id}",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an editable clinical care plan",
)
def update_care_plan_endpoint(
    care_plan_id: str,
    plan_in: CarePlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CarePlanResponse:
    """Update care plan goals, interventions, or descriptions."""
    return update_care_plan(
        db=db,
        plan_id=care_plan_id,
        plan_in=plan_in,
        current_user=current_user,
    )


@router.post(
    "/care-plans/{care_plan_id}/review",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Physician review, signoff, and activation of a care plan",
)
def review_care_plan_endpoint(
    care_plan_id: str,
    review_in: CarePlanReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> CarePlanResponse:
    """Attending physician signoff and activation."""
    return review_care_plan(
        db=db,
        plan_id=care_plan_id,
        review_in=review_in,
        current_user=current_user,
    )


@router.post(
    "/care-plans/{care_plan_id}/complete",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark an active care plan as completed",
)
def complete_care_plan_endpoint(
    care_plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CarePlanResponse:
    """Mark a care plan as completed."""
    return complete_care_plan(
        db=db,
        plan_id=care_plan_id,
        current_user=current_user,
    )


@router.post(
    "/care-plans/{care_plan_id}/cancel",
    response_model=CarePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel or suspend a care plan",
)
def cancel_care_plan_endpoint(
    care_plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> CarePlanResponse:
    """Cancel a care plan."""
    return cancel_care_plan(
        db=db,
        plan_id=care_plan_id,
        current_user=current_user,
    )


@router.post(
    "/tasks/care-plans/synthesize",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue AI-assisted Care Plan synthesis background task",
)
def enqueue_care_plan_synthesis_endpoint(
    patient_id: str = Query(..., description="Target patient identifier"),
    synth_in: Optional[CarePlanSynthesizeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> BackgroundTaskResponse:
    """Enqueue AI care plan drafting."""
    task = enqueue_care_plan_synthesis(
        db=db,
        patient_id=patient_id,
        synth_in=synth_in or CarePlanSynthesizeRequest(),
        current_user=current_user,
    )
    return BackgroundTaskResponse.model_validate(task)


# ==============================================================================
# CARE TASKS & FOLLOW-UPS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/care-tasks",
    response_model=CareTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new clinical follow-up task",
)
def create_care_task_endpoint(
    patient_id: str,
    task_in: CareTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CareTaskResponse:
    """Create a clinical follow-up task."""
    return create_care_task(
        db=db,
        patient_id=patient_id,
        task_in=task_in,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/care-tasks",
    response_model=CareTaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical follow-up tasks for a patient",
)
def list_patient_care_tasks_endpoint(
    patient_id: str,
    care_plan_id: Optional[str] = Query(None, description="Filter tasks by associated care plan ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter tasks by status (pending, completed, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CareTaskListResponse:
    """List clinical follow-up tasks."""
    return list_patient_care_tasks(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        care_plan_id=care_plan_id,
        status_filter=status_filter,
    )


@router.get(
    "/care-tasks/{care_task_id}",
    response_model=CareTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve details of a specific care task",
)
def get_care_task_endpoint(
    care_task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CareTaskResponse:
    """Retrieve details of a care task."""
    return get_care_task(
        db=db,
        task_id=care_task_id,
        current_user=current_user,
    )


@router.patch(
    "/care-tasks/{care_task_id}",
    response_model=CareTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing clinical care task",
)
def update_care_task_endpoint(
    care_task_id: str,
    task_in: CareTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CareTaskResponse:
    """Update a care task."""
    return update_care_task(
        db=db,
        task_id=care_task_id,
        task_in=task_in,
        current_user=current_user,
    )


@router.post(
    "/care-tasks/{care_task_id}/complete",
    response_model=CareTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a clinical follow-up task as complete with outcome notes",
)
def complete_care_task_endpoint(
    care_task_id: str,
    complete_in: Optional[CareTaskCompleteRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> CareTaskResponse:
    """Mark a care task as complete."""
    return complete_care_task(
        db=db,
        task_id=care_task_id,
        complete_in=complete_in or CareTaskCompleteRequest(),
        current_user=current_user,
    )

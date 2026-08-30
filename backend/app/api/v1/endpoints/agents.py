"""FastAPI router endpoints for Clinical AI Agents & Autonomous Care Coordination.

Phase 9.0.17: Advanced Clinical AI Agents & Autonomous Care Coordination.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_role
from app.ai.task_worker import get_background_task_provider

from app.models.agents import ClinicalAgentRecommendation, ClinicalAgentRun
from app.models.user import User, UserRole
from app.schemas.agents import (
    AgentRunStatus,
    AgentType,
    ApprovalStatus,
    CareCoordinationSynthesisResponse,
    ClinicalAgentDefinitionListResponse,
    ClinicalAgentDefinitionResponse,
    ClinicalAgentRecommendationResponse,
    ClinicalAgentRecommendationReviewRequest,
    ClinicalAgentRunCreateRequest,
    ClinicalAgentRunDetailResponse,
    ClinicalAgentRunListResponse,
    ClinicalAgentRunResponse,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType
from app.services.clinical_agent_service import clinical_agent_service

router = APIRouter(prefix="/agents", tags=["Clinical AI Agents & Care Coordination"])


# ==============================================================================
# 1. AGENT DEFINITIONS & REGISTRY
# ==============================================================================

@router.get(
    "/definitions",
    response_model=ClinicalAgentDefinitionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered clinical AI agent definitions and capability metadata",
)
def list_agent_definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalAgentDefinitionListResponse:
    """Retrieve all available specialized clinical AI agents."""
    agents = clinical_agent_service.seed_default_agents(db)
    items = [ClinicalAgentDefinitionResponse.model_validate(a) for a in agents]
    return ClinicalAgentDefinitionListResponse(items=items, total=len(items))


# ==============================================================================
# 2. AGENT EXECUTION RUNS
# ==============================================================================

@router.post(
    "/runs",
    response_model=ClinicalAgentRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a specialized or master clinical AI agent run",
)
def trigger_agent_run(
    req: ClinicalAgentRunCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> ClinicalAgentRunDetailResponse:
    """Execute multi-agent care coordination reasoning and generate structured recommendations."""
    try:
        run = clinical_agent_service.trigger_agent_run(
            db=db,
            patient_id_or_str=req.patient_id,
            agent_type=req.agent_type.value,
            initiated_by_user_id=current_user.id,
            include_subagents=[s.value for s in req.include_subagents] if req.include_subagents else None,
        )

        full_run = clinical_agent_service.get_agent_run(db, run.id)
        run_dto = ClinicalAgentRunDetailResponse.model_validate(full_run)
        run_dto.patient_identifier = full_run.patient.patient_id if full_run.patient else None
        run_dto.patient_name = f"{full_run.patient.first_name} {full_run.patient.last_name}" if full_run.patient else None
        run_dto.initiated_by_name = full_run.initiated_by_user.name if full_run.initiated_by_user else None
        run_dto.recommendations_count = len(full_run.recommendations)
        return run_dto
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/runs",
    response_model=ClinicalAgentRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical AI agent runs with filtering",
)
def list_agent_runs(
    patient_id: Optional[str] = Query(None, description="Filter by patient identifier"),
    status: Optional[AgentRunStatus] = Query(None, description="Filter by run status"),
    agent_type: Optional[AgentType] = Query(None, description="Filter by agent type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalAgentRunListResponse:
    """Query historical agent execution runs with RBAC isolation."""
    if current_user.role == UserRole.PATIENT and patient_id:
        patient = clinical_agent_service._resolve_patient(db, patient_id)
        if patient.email != current_user.email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested patient runs.")

    runs = clinical_agent_service.list_agent_runs(
        db=db,
        patient_id_or_str=patient_id,
        status=status.value if status else None,
        agent_type=agent_type.value if agent_type else None,
        skip=skip,
        limit=limit,
    )

    items = []
    for r in runs:
        r_dto = ClinicalAgentRunResponse.model_validate(r)
        r_dto.patient_identifier = r.patient.patient_id if r.patient else None
        r_dto.patient_name = f"{r.patient.first_name} {r.patient.last_name}" if r.patient else None
        r_dto.initiated_by_name = r.initiated_by_user.name if r.initiated_by_user else None
        r_dto.recommendations_count = len(r.recommendations)
        items.append(r_dto)

    return ClinicalAgentRunListResponse(items=items, total=len(items))


@router.get(
    "/runs/{run_id}",
    response_model=ClinicalAgentRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detailed agent run, recommendations, and evidence references",
)
def get_agent_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalAgentRunDetailResponse:
    """Retrieve full agent run audit trail and criterion explainability."""
    run = clinical_agent_service.get_agent_run(db, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent run '{run_id}' was not found.")

    if current_user.role == UserRole.PATIENT and run.patient and run.patient.email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested agent run.")

    run_dto = ClinicalAgentRunDetailResponse.model_validate(run)
    run_dto.patient_identifier = run.patient.patient_id if run.patient else None
    run_dto.patient_name = f"{run.patient.first_name} {run.patient.last_name}" if run.patient else None
    run_dto.initiated_by_name = run.initiated_by_user.name if run.initiated_by_user else None
    run_dto.recommendations_count = len(run.recommendations)
    return run_dto


# ==============================================================================
# 3. CLINICIAN REVIEW & RECOMMENDATION ACTIONS
# ==============================================================================

@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=ClinicalAgentRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician approval of an agent recommendation",
)
def approve_agent_recommendation(
    recommendation_id: str,
    req: ClinicalAgentRecommendationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> ClinicalAgentRecommendationResponse:
    """Record formal clinician approval on an agent recommendation with review notes."""
    try:
        rec = clinical_agent_service.review_recommendation(
            db=db,
            rec_id_or_int=recommendation_id,
            approval_status=ApprovalStatus.APPROVED.value,
            reviewed_by_user_id=current_user.id,
            review_notes=req.review_notes,
        )
        rec_dto = ClinicalAgentRecommendationResponse.model_validate(rec)
        rec_dto.reviewed_by_name = current_user.name
        return rec_dto
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=ClinicalAgentRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician rejection of an agent recommendation",
)
def reject_agent_recommendation(
    recommendation_id: str,
    req: ClinicalAgentRecommendationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> ClinicalAgentRecommendationResponse:
    """Record formal clinician rejection on an agent recommendation with documented rationale."""
    try:
        rec = clinical_agent_service.review_recommendation(
            db=db,
            rec_id_or_int=recommendation_id,
            approval_status=ApprovalStatus.REJECTED.value,
            reviewed_by_user_id=current_user.id,
            review_notes=req.review_notes,
        )
        rec_dto = ClinicalAgentRecommendationResponse.model_validate(rec)
        rec_dto.reviewed_by_name = current_user.name
        return rec_dto
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/runs/{run_id}/execute",
    response_model=ClinicalAgentRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute approved recommendations for an agent run",
)
def execute_approved_run_actions(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> ClinicalAgentRunDetailResponse:
    """Execute all approved recommendations in a run (creating CareTasks where applicable)."""
    run = clinical_agent_service.get_agent_run(db, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent run '{run_id}' was not found.")

    for rec in run.recommendations:
        if rec.approval_status == "approved" and rec.execution_status != "completed":
            clinical_agent_service.execute_approved_recommendation(db, rec.id, current_user.id)

    db.refresh(run)
    run_dto = ClinicalAgentRunDetailResponse.model_validate(run)
    run_dto.patient_identifier = run.patient.patient_id if run.patient else None
    run_dto.patient_name = f"{run.patient.first_name} {run.patient.last_name}" if run.patient else None
    run_dto.initiated_by_name = run.initiated_by_user.name if run.initiated_by_user else None
    run_dto.recommendations_count = len(run.recommendations)
    return run_dto


# ==============================================================================
# 4. PATIENT-SCOPED CARE COORDINATION ENDPOINTS
# ==============================================================================

@router.get(
    "/patients/{patient_id}/care-coordination",
    response_model=CareCoordinationSynthesisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest synthesized care coordination recommendations for a patient",
)
def get_patient_care_coordination(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CareCoordinationSynthesisResponse:
    """Retrieve the most recent care coordination recommendations and status."""
    try:
        patient = clinical_agent_service._resolve_patient(db, patient_id)
        if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested patient context.")

        runs = clinical_agent_service.list_agent_runs(db, patient_id_or_str=patient.id, limit=1)
        if runs:
            full_run = clinical_agent_service.get_agent_run(db, runs[0].id)
            recs_out = []
            for r in full_run.recommendations:
                r_dto = ClinicalAgentRecommendationResponse.model_validate(r)
                r_dto.reviewed_by_name = r.reviewed_by_user.name if r.reviewed_by_user else None
                recs_out.append(r_dto)

            urgent_count = sum(1 for r in full_run.recommendations if r.priority == "urgent")
            high_count = sum(1 for r in full_run.recommendations if r.priority == "high")
            pending_count = sum(1 for r in full_run.recommendations if r.approval_status == "pending_review")

            return CareCoordinationSynthesisResponse(
                patient_id=patient.patient_id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                run_id=full_run.run_id,
                status=AgentRunStatus(full_run.status),
                overall_summary=full_run.overall_summary or "Active care coordination plan.",
                provenance_hash=full_run.provenance_hash,
                urgent_recommendations_count=urgent_count,
                high_recommendations_count=high_count,
                pending_approvals_count=pending_count,
                recommendations=recs_out,
            )
        else:
            # Trigger fresh synthesis
            return clinical_agent_service.synthesize_care_coordination(db, patient.id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/patients/{patient_id}/care-coordination/synthesize",
    response_model=CareCoordinationSynthesisResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger one-click comprehensive multi-agent care coordination synthesis",
)
def synthesize_patient_care_coordination(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> CareCoordinationSynthesisResponse:
    """Force re-synthesis of multi-agent care coordination plan."""
    try:
        return clinical_agent_service.synthesize_care_coordination(db, patient_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/tasks/patients/{patient_id}/care-coordination",
    response_model=BackgroundTask,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous care coordination synthesis task",
)
def enqueue_care_coordination_task(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF)),
) -> BackgroundTask:
    """Enqueue background asynchronous care coordination task."""
    try:
        patient = clinical_agent_service._resolve_patient(db, patient_id)
        task_provider = get_background_task_provider()
        task = task_provider.submit_task(
            task_type=BackgroundTaskType.CARE_COORDINATION_SYNTHESIS,
            fn=lambda p_id=patient.patient_id: clinical_agent_service.synthesize_care_coordination(db, p_id, current_user.id).model_dump(),
            patient_id=patient.patient_id,
            created_by_user_id=current_user.id,
        )
        return task
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

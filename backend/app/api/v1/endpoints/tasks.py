"""Background Asynchronous Task API Endpoints.

Phase 9.0.3: Background Asynchronous Worker Architecture.

Endpoints:
- POST /api/v1/tasks/documents/{document_id}/process : Enqueue async document extraction & indexing
- POST /api/v1/tasks/timeline/{patient_id}/summary   : Enqueue async clinical timeline compilation
- GET  /api/v1/tasks/{task_id}                      : Retrieve task execution status and progress
- GET  /api/v1/tasks                                : List authorized tasks with filtering & pagination
- POST /api/v1/tasks/{task_id}/retry                : Retry a failed or cancelled background task
- POST /api/v1/tasks/{task_id}/cancel               : Cancel a queued background task
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.task import (
    BackgroundTaskResponse,
    BackgroundTaskStatus,
    BackgroundTaskType,
    DocumentTaskRequest,
    TaskListResponse,
    TimelineTaskRequest,
)
from app.services.task_service import (
    build_task_response,
    cancel_task_for_user,
    enqueue_document_processing_task,
    enqueue_timeline_summary_task,
    get_task_status,
    list_tasks_for_user,
    retry_task_for_user,
)

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.post(
    "/documents/{document_id}/process",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous document processing task",
)
def enqueue_document_processing(
    document_id: str,
    request: DocumentTaskRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Trigger background extraction, chunking, and vector indexing for a medical document."""
    try:
        task = enqueue_document_processing_task(
            db=db,
            document_ref=document_id,
            current_user=current_user,
        )
        return build_task_response(task)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/timeline/{patient_id}/summary",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous clinical timeline compilation",
)
def enqueue_timeline_compilation(
    patient_id: str,
    request: TimelineTaskRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Trigger background compilation of patient longitudinal timeline summary."""
    try:
        focus = request.focus if request else None
        task = enqueue_timeline_summary_task(
            db=db,
            patient_id_str=patient_id,
            current_user=current_user,
            focus=focus,
        )
        return build_task_response(task)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/{task_id}",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve background task status and execution progress",
)
def get_task_status_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Query task status, completion metrics, or failure diagnostics."""
    try:
        task = get_task_status(db=db, task_id=task_id, current_user=current_user)
        return build_task_response(task)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List background tasks with filtering",
)
def list_tasks_endpoint(
    patient_id: str | None = Query(None, description="Filter by target patient ID"),
    status_filter: BackgroundTaskStatus | None = Query(None, alias="status", description="Filter by task status"),
    task_type: BackgroundTaskType | None = Query(None, description="Filter by task type"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TaskListResponse:
    """Retrieve paginated list of authorized background tasks."""
    try:
        tasks, total = list_tasks_for_user(
            db=db,
            current_user=current_user,
            patient_id=patient_id,
            status=status_filter,
            task_type=task_type,
            page=page,
            size=size,
        )
        items = [build_task_response(t) for t in tasks]
        return TaskListResponse.create(items=items, total=total, page=page, size=size)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/{task_id}/retry",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry a failed or cancelled background task",
)
def retry_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Re-enqueue a failed or cancelled task for execution."""
    try:
        task = retry_task_for_user(db=db, task_id=task_id, current_user=current_user)
        return build_task_response(task)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{task_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a queued background task",
)
def cancel_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Cancel a pending background task before or during execution."""
    try:
        cancelled = cancel_task_for_user(db=db, task_id=task_id, current_user=current_user)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task '{task_id}' cannot be cancelled (it may have already completed or failed).",
            )
        return {"detail": f"Task '{task_id}' was successfully cancelled."}
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

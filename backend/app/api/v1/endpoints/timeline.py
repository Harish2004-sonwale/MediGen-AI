"""API Router for Longitudinal Clinical Timeline.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.timeline import (
    TimelineEventType,
    TimelineListResponse,
    TimelineSummaryResponse,
)
from app.services.timeline_service import (
    get_patient_timeline,
    get_patient_timeline_summary,
)

router = APIRouter(tags=["Clinical Timeline"])


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string to timezone-aware UTC datetime."""
    if not dt_str:
        return None
    clean = dt_str.strip().replace("Z", "+00:00").replace(" ", "+")
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


@router.get(
    "/patients/{patient_id}/timeline",
    response_model=TimelineListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve longitudinal clinical timeline for a patient",
)
def get_timeline(
    patient_id: str,
    start_date: Optional[str] = Query(None, description="Filter events on or after this ISO timestamp"),
    end_date: Optional[str] = Query(None, description="Filter events on or before this ISO timestamp"),
    event_type: Optional[TimelineEventType] = Query(None, description="Filter by event category"),
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order by event_date (asc or desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TimelineListResponse:
    """Retrieve an authenticated, patient-scoped longitudinal timeline of encounters, appointments, documents, and clinical events."""
    try:
        s_dt = _parse_dt(start_date)
        e_dt = _parse_dt(end_date)
        return get_patient_timeline(
            db=db,
            patient_id_str=patient_id,
            current_user=current_user,
            start_date=s_dt,
            end_date=e_dt,
            event_type=event_type,
            skip=skip,
            limit=limit,
            sort_order=sort_order,
        )
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
    "/patients/{patient_id}/timeline/summary",
    response_model=TimelineSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a grounded longitudinal clinical summary",
)
def get_timeline_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TimelineSummaryResponse:
    """Generate a RAG-grounded longitudinal narrative summary of patient history with verified citations."""
    try:
        return get_patient_timeline_summary(
            db=db,
            patient_id_str=patient_id,
            current_user=current_user,
        )
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

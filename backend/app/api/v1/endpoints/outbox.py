"""Transactional Outbox and Dead-Letter Queue Monitoring Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.database import get_db
from app.models.outbox import OutboxEvent
from app.models.user import User
from app.schemas.outbox import (
    OutboxEventResponse,
    OutboxMetricsResponse,
    OutboxReplayRequest,
    OutboxReplayResponse,
)
from app.schemas.user import UserRole
from app.services.outbox_service import get_outbox_metrics, prune_published_outbox_events, replay_dead_letter_events

router = APIRouter(prefix="/outbox", tags=["Transactional Outbox & Reliability"])


@router.get("/events", response_model=list[OutboxEventResponse])
def list_outbox_events(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[OutboxEvent]:
    """List recent outbox events with optional status filtering."""
    stmt = select(OutboxEvent)
    if status_filter:
        stmt = stmt.where(OutboxEvent.status == status_filter.upper())
    stmt = stmt.order_by(OutboxEvent.created_at.desc()).offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post("/replay", response_model=OutboxReplayResponse)
def replay_dlq_events(
    payload: OutboxReplayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> OutboxReplayResponse:
    """Replay dead-lettered events back to PENDING status for Celery processing."""
    replayed = replay_dead_letter_events(db, event_ids=payload.event_ids)
    return OutboxReplayResponse(
        replayed_count=replayed,
        message=f"Successfully queued {replayed} dead-lettered outbox event(s) for replay.",
    )


@router.get("/metrics", response_model=OutboxMetricsResponse)
def get_outbox_telemetry_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OutboxMetricsResponse:
    """Retrieve aggregate reliability metrics for outbox events."""
    metrics = get_outbox_metrics(db)
    return OutboxMetricsResponse(**metrics)


@router.post("/prune", status_code=status.HTTP_200_OK)
def prune_outbox_events(
    retention_days: int = Query(30, ge=1, le=365, description="Minimum age in days of PUBLISHED events to prune"),
    batch_size: int = Query(500, ge=1, le=5000, description="Records to delete per batch"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict:
    """Prune aged PUBLISHED outbox events. Only PUBLISHED events older than retention_days are deleted.
    PENDING, FAILED, and DEAD_LETTER events are never pruned. Idempotent and safe to run repeatedly."""
    result = prune_published_outbox_events(db, retention_days=retention_days, batch_size=batch_size)
    return {
        "message": f"Pruned {result['deleted']} published outbox event(s) older than {retention_days} day(s).",
        **result,
    }

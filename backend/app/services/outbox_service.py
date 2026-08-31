"""Transactional Outbox Service for Reliable At-Least-Once Domain Event Dispatch."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outbox import OutboxEvent


def record_outbox_event(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    facility_id: Optional[str] = None,
    max_attempts: int = 5,
) -> OutboxEvent:
    """Atomically persist a domain event within the active database transaction."""
    event = OutboxEvent(
        event_id=f"EVT-{uuid.uuid4().hex[:16].upper()}",
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        facility_id=facility_id or "FAC-001",
        payload_json=payload,
        status="PENDING",
        attempts=0,
        max_attempts=max_attempts,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event


def fetch_pending_outbox_events(
    db: Session,
    limit: int = 50,
) -> list[OutboxEvent]:
    """Retrieve pending or retryable outbox events eligible for dispatch."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(OutboxEvent)
        .where(
            (OutboxEvent.status == "PENDING")
            | (
                (OutboxEvent.status == "FAILED")
                & (OutboxEvent.attempts < OutboxEvent.max_attempts)
                & ((OutboxEvent.retry_after.is_(None)) | (OutboxEvent.retry_after <= now))
            )
        )
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def mark_outbox_event_published(
    db: Session,
    event_id: str,
) -> Optional[OutboxEvent]:
    """Mark an outbox event as successfully delivered."""
    stmt = select(OutboxEvent).where(OutboxEvent.event_id == event_id)
    event = db.execute(stmt).scalars().first()
    if event:
        event.status = "PUBLISHED"
        event.published_at = datetime.now(timezone.utc)
        event.last_error = None
        db.commit()
        db.refresh(event)
    return event


def mark_outbox_event_failed(
    db: Session,
    event_id: str,
    error_message: str,
    backoff_base_seconds: int = 10,
) -> Optional[OutboxEvent]:
    """Record a delivery attempt failure with exponential backoff or dead-letter transition."""
    stmt = select(OutboxEvent).where(OutboxEvent.event_id == event_id)
    event = db.execute(stmt).scalars().first()
    if not event:
        return None

    event.attempts += 1
    event.last_error = error_message

    if event.attempts >= event.max_attempts:
        event.status = "DEAD_LETTER"
        event.retry_after = None
    else:
        event.status = "FAILED"
        delay = backoff_base_seconds * (2 ** (event.attempts - 1))
        event.retry_after = datetime.now(timezone.utc) + timedelta(seconds=delay)

    db.commit()
    db.refresh(event)
    return event


def replay_dead_letter_events(
    db: Session,
    event_ids: Optional[list[str]] = None,
) -> int:
    """Reset dead-lettered events back to PENDING for re-dispatch."""
    stmt = select(OutboxEvent).where(OutboxEvent.status == "DEAD_LETTER")
    if event_ids:
        stmt = stmt.where(OutboxEvent.event_id.in_(event_ids))

    events = list(db.execute(stmt).scalars().all())
    count = 0
    for event in events:
        event.status = "PENDING"
        event.attempts = 0
        event.last_error = None
        event.retry_after = None
        count += 1

    if count > 0:
        db.commit()
    return count


def get_outbox_metrics(db: Session) -> dict[str, int]:
    """Return summary counts of outbox events by status."""
    stmt = select(OutboxEvent.status, OutboxEvent.id)
    results = db.execute(stmt).all()
    metrics: dict[str, int] = {
        "pending": 0,
        "published": 0,
        "failed": 0,
        "dead_letter": 0,
        "total": len(results),
    }
    for status, _ in results:
        status_key = status.lower()
        if status_key in metrics:
            metrics[status_key] += 1
    return metrics

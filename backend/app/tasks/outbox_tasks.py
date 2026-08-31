"""Celery Background Tasks for Transactional Outbox Event Dispatch."""

import logging
from typing import Any
from app.database import SessionLocal
from app.services.outbox_service import (
    fetch_pending_outbox_events,
    mark_outbox_event_failed,
    mark_outbox_event_published,
)

logger = logging.getLogger("medigen.outbox")


def process_outbox_events_sync(batch_size: int = 50) -> dict[str, Any]:
    """Synchronous worker function to fetch and dispatch pending outbox events."""
    db = SessionLocal()
    processed = 0
    failed = 0
    try:
        events = fetch_pending_outbox_events(db, limit=batch_size)
        for event in events:
            try:
                # Dispatch event to target topic/channel/handler
                logger.info(
                    "Dispatching outbox event: event_id=%s type=%s aggregate=%s:%s",
                    event.event_id,
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                )
                # In real production, this routes to Kafka, RabbitMQ, external webhooks, or internal handlers.
                mark_outbox_event_published(db, event.event_id)
                processed += 1
            except Exception as exc:
                logger.error("Failed to dispatch outbox event %s: %s", event.event_id, str(exc))
                mark_outbox_event_failed(db, event.event_id, error_message=str(exc))
                failed += 1
        return {"processed": processed, "failed": failed, "total_scanned": len(events)}
    finally:
        db.close()

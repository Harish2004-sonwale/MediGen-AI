"""Celery Background Tasks for Transactional Outbox Event Dispatch."""

import logging
from typing import Any
from app.core.websocket_manager import websocket_manager
from app.database import SessionLocal
from app.services.fhir_subscription_service import deliver_subscription_notifications_sync
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
                logger.info(
                    "Dispatching outbox event: event_id=%s type=%s aggregate=%s:%s",
                    event.event_id,
                    event.event_type,
                    event.aggregate_type,
                    event.aggregate_id,
                )

                # 1. Deliver to matching active FHIR Subscriptions
                try:
                    deliver_subscription_notifications_sync(
                        db=db,
                        event_type=event.event_type,
                        payload=event.payload_json,
                        facility_id=event.facility_id,
                    )
                except Exception as sub_exc:
                    logger.warning("Subscription delivery error for %s: %s", event.event_id, sub_exc)

                # 2. Publish real-time notifications to WebSocket telemetry rooms if relevant
                if "alert" in event.event_type or "telemetry" in event.event_type or "order" in event.event_type:
                    try:
                        import asyncio
                        room = f"telemetry_{event.facility_id or 'FAC-001'}"
                        msg = {
                            "type": "DOMAIN_EVENT",
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "aggregate": f"{event.aggregate_type}:{event.aggregate_id}",
                            "data": event.payload_json,
                        }
                        # Non-blocking broadcast
                        asyncio.run(websocket_manager.broadcast_to_room(room, msg))
                    except Exception:
                        pass

                # 3. Mark event as successfully published
                mark_outbox_event_published(db, event.event_id)
                processed += 1
            except Exception as exc:
                logger.error("Failed to dispatch outbox event %s: %s", event.event_id, str(exc))
                mark_outbox_event_failed(db, event.event_id, error_message=str(exc))
                failed += 1
        return {"processed": processed, "failed": failed, "total_scanned": len(events)}
    finally:
        db.close()

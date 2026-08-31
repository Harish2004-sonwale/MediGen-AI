"""Service for HL7 FHIR R4 Topic Subscriptions and Event Notification Fan-out."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fhir_subscription import FHIRSubscription
from app.schemas.fhir_subscription import FHIRSubscriptionCreate, FHIRSubscriptionUpdate

logger = logging.getLogger("medigen.fhir.subscriptions")


def create_fhir_subscription(
    db: Session,
    payload: FHIRSubscriptionCreate,
) -> FHIRSubscription:
    """Register a new FHIR topic subscription."""
    sub_id = f"SUB-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    subscription = FHIRSubscription(
        subscription_id=sub_id,
        facility_id=payload.facility_id or "FAC-001",
        topic=payload.topic,
        criteria=payload.criteria,
        channel_type=payload.channel_type.upper(),
        endpoint_url=payload.endpoint_url,
        secret_token=payload.secret_token,
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    logger.info("Created FHIR subscription %s for topic '%s'", sub_id, payload.topic)
    return subscription


def list_fhir_subscriptions(
    db: Session,
    facility_id: Optional[str] = None,
    topic: Optional[str] = None,
) -> List[FHIRSubscription]:
    """List active subscriptions filtered by facility or topic."""
    stmt = select(FHIRSubscription)
    if facility_id:
        stmt = stmt.where(FHIRSubscription.facility_id == facility_id)
    if topic:
        stmt = stmt.where(FHIRSubscription.topic == topic)
    stmt = stmt.order_by(FHIRSubscription.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_fhir_subscription(db: Session, subscription_id: str) -> Optional[FHIRSubscription]:
    """Retrieve a single subscription by ID."""
    stmt = select(FHIRSubscription).where(FHIRSubscription.subscription_id == subscription_id)
    return db.execute(stmt).scalars().first()


def delete_fhir_subscription(db: Session, subscription_id: str) -> bool:
    """Delete a subscription."""
    sub = get_fhir_subscription(db, subscription_id)
    if not sub:
        return False
    db.delete(sub)
    db.commit()
    return True


async def dispatch_subscription_notification(
    subscription: FHIRSubscription,
    event_type: str,
    payload: Dict[str, Any],
) -> bool:
    """Send async webhook notification for a matched topic event."""
    if subscription.channel_type != "REST_HOOK" or not subscription.endpoint_url:
        return False

    headers = {
        "Content-Type": "application/fhir+json",
        "X-Subscription-ID": subscription.subscription_id,
        "X-Event-Type": event_type,
    }
    if subscription.secret_token:
        headers["Authorization"] = f"Bearer {subscription.secret_token}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(subscription.endpoint_url, json=payload, headers=headers)
            return resp.status_code < 400
    except Exception as exc:
        logger.warning("Failed to dispatch subscription notification to %s: %s", subscription.endpoint_url, exc)
        return False

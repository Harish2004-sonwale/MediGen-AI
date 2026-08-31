"""Clinical Alert Escalation Engine for Unacknowledged Critical Telemetry and CDS Events."""

from datetime import datetime, timedelta, timezone
import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.schemas.alert import AlertSeverity, AlertStatus
from app.services.outbox_service import record_outbox_event

logger = logging.getLogger("medigen.alerts.escalation")


def scan_and_escalate_unacknowledged_alerts(
    db: Session,
    tier1_threshold_minutes: int = 15,
    tier2_threshold_minutes: int = 30,
) -> List[ClinicalAlert]:
    """Scan active critical/high severity alerts and escalate unacknowledged events with outbox notifications."""
    now = datetime.now(timezone.utc)
    cutoff_tier1 = now - timedelta(minutes=tier1_threshold_minutes)
    cutoff_tier2 = now - timedelta(minutes=tier2_threshold_minutes)

    critical_severities = [AlertSeverity.CRITICAL, AlertSeverity.HIGH]

    stmt = (
        select(ClinicalAlert)
        .where(
            ClinicalAlert.status == AlertStatus.ACTIVE,
            ClinicalAlert.severity.in_(critical_severities),
            ClinicalAlert.acknowledged_at.is_(None),
            ClinicalAlert.created_at <= cutoff_tier1,
        )
    )
    alerts = list(db.execute(stmt).scalars().all())
    escalated_alerts: List[ClinicalAlert] = []

    for alert in alerts:
        old_level = alert.escalation_level or 0
        new_level = old_level

        if alert.created_at <= cutoff_tier2 and old_level < 2:
            new_level = 2
            alert.escalation_notes = (
                f"Tier 2 Escalation: Critical alert unacknowledged for >{tier2_threshold_minutes} min. "
                "Dispatched urgent page to Rapid Response Team & Clinical Supervisor."
            )
        elif alert.created_at <= cutoff_tier1 and old_level < 1:
            new_level = 1
            alert.escalation_notes = (
                f"Tier 1 Escalation: Critical alert unacknowledged for >{tier1_threshold_minutes} min. "
                "Dispatched notification to Charge Nurse & Attending Physician."
            )

        if new_level > old_level:
            alert.escalation_level = new_level
            alert.escalated_at = now
            record_outbox_event(
                db=db,
                event_type="ALERT_ESCALATED",
                aggregate_type="CLINICAL_ALERT",
                aggregate_id=alert.alert_id,
                payload={
                    "alert_id": alert.alert_id,
                    "patient_id": alert.patient_id,
                    "title": alert.title,
                    "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                    "escalation_level": new_level,
                    "escalated_at": now.isoformat(),
                    "escalation_notes": alert.escalation_notes,
                },
                facility_id=alert.facility_id or "FAC-001",
            )
            escalated_alerts.append(alert)
            logger.warning(
                "Escalated alert %s for patient %s to Level %d: %s",
                alert.alert_id,
                alert.patient_id,
                new_level,
                alert.title,
            )

    if escalated_alerts:
        db.commit()
        for a in escalated_alerts:
            db.refresh(a)

    return escalated_alerts

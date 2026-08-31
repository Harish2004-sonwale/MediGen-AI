"""Celery Background Tasks for Cryptographic Audit Trail Hash Chain Integrity Verification.

Phase 9.0.24: Enterprise Audit Governance & Automated Cryptographic Chain Verification.
"""

import logging
from typing import Any
from app.database import SessionLocal
from app.services.audit_service import audit_service
from app.services.outbox_service import record_outbox_event

logger = logging.getLogger("medigen.audit_tasks")


def verify_audit_log_integrity_task(db: Any = None) -> dict[str, Any]:
    """Execute cryptographic SHA-256 hash-chain verification of all clinical audit events.

    Reuses authoritative AuditService verification without altering audit records.
    If tampering or broken hash continuity is detected:
    - Logs a CRITICAL security event.
    - Atomically enqueues an 'audit-chain-tamper-detected' outbox event.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        logger.info("Starting cryptographic audit log integrity verification sweep.")
        res = audit_service.verify_audit_trail_integrity(db)

        result_dict = {
            "status": res.status,
            "total_records_checked": res.total_records_checked,
            "tamper_detected": res.tamper_detected,
            "broken_links_count": res.broken_links_count,
            "tampered_event_ids": res.tampered_event_ids,
            "chain_head_hash": res.chain_head_hash,
            "verified_at": res.verified_at.isoformat() if res.verified_at else None,
        }

        if res.tamper_detected:
            logger.critical(
                "CRITICAL SECURITY ALERT: Audit log hash chain integrity verification failed! "
                "Total checked: %d, Broken links: %d, Tampered event IDs: %s",
                res.total_records_checked,
                res.broken_links_count,
                res.tampered_event_ids,
            )
            # Enqueue transactional outbox event for security incident alerting
            try:
                record_outbox_event(
                    db=db,
                    event_type="audit-chain-tamper-detected",
                    aggregate_type="AuditChain",
                    aggregate_id=res.tampered_event_ids[0] if res.tampered_event_ids else "AUDIT_CHAIN",
                    facility_id="FAC-001",
                    payload={
                        "status": "COMPROMISED",
                        "total_records_checked": res.total_records_checked,
                        "broken_links_count": res.broken_links_count,
                        "tampered_event_ids": res.tampered_event_ids,
                        "chain_head_hash": res.chain_head_hash,
                    },
                )
                db.commit()
            except Exception as outbox_exc:
                logger.error("Failed to enqueue audit tamper outbox event: %s", outbox_exc)
        else:
            logger.info(
                "Audit log integrity sweep completed successfully. %d records verified (Status: VALID).",
                res.total_records_checked,
            )

        return result_dict
    finally:
        if close_db:
            db.close()

from datetime import datetime, timezone
import secrets
from typing import Any, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.observability import sanitize_log_message
from app.models.security import AuditAction, AuditOutcome, ClinicalAuditEvent
from app.schemas.security import (
    AuditEventListResponse,
    AuditIntegrityVerificationResponse,
    ClinicalAuditEventResponse,
)


class AuditService:
    """Enterprise clinical audit logging service with SHA-256 tamper-evident hash chaining."""

    GENESIS_PREV_HASH = "0" * 64

    @staticmethod
    def _sanitize_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Strip raw PHI, tokens, and passwords from metadata dictionary."""
        if not metadata:
            return {}
        clean: dict[str, Any] = {}
        for k, v in metadata.items():
            key_lower = k.lower()
            if any(forbidden in key_lower for forbidden in ["password", "secret", "token", "auth_header", "bearer"]):
                clean[k] = "[REDACTED]"
            elif isinstance(v, str):
                clean[k] = sanitize_log_message(v)
            elif isinstance(v, (dict, list, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean

    def emit_audit_event(
        self,
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[int] = None,
        user_role: str = "ANONYMOUS",
        patient_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        purpose_of_use: str = "TREATMENT",
        outcome: str = AuditOutcome.SUCCESS,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ClinicalAuditEvent:
        """Create and append an immutable audit record with cryptographic hash chain."""
        # 1. Fetch latest audit event in chain
        latest_event = db.scalars(
            select(ClinicalAuditEvent).order_by(desc(ClinicalAuditEvent.id)).limit(1)
        ).first()

        prev_hash = latest_event.record_hash if latest_event else self.GENESIS_PREV_HASH

        # 2. Generate unique event ID
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        event_id = f"AUD-{date_str}-{secrets.token_hex(6).upper()}"
        now_dt = datetime.now(timezone.utc)
        timestamp_iso = now_dt.isoformat()

        # 3. Clean metadata
        clean_metadata = self._sanitize_metadata(metadata)

        # 4. Compute cryptographic SHA-256 record hash
        record_hash = ClinicalAuditEvent.calculate_hash(
            prev_hash=prev_hash,
            event_id=event_id,
            timestamp_iso=timestamp_iso,
            user_id=user_id,
            patient_id=patient_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
        )

        # 5. Persist audit record
        audit_record = ClinicalAuditEvent(
            event_id=event_id,
            timestamp=now_dt,
            user_id=user_id,
            user_role=user_role,
            patient_id=patient_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            purpose_of_use=purpose_of_use,
            outcome=outcome,
            metadata_json=clean_metadata,
            prev_record_hash=prev_hash,
            record_hash=record_hash,
        )

        db.add(audit_record)
        db.commit()
        db.refresh(audit_record)

        # 6. Stream to external SIEM if configured
        try:
            from app.core.audit_streaming import stream_audit_event
            stream_audit_event(audit_record)
        except Exception:
            pass

        return audit_record

    def verify_audit_trail_integrity(self, db: Session) -> AuditIntegrityVerificationResponse:
        """Walk the cryptographic SHA-256 hash chain and detect any modified or deleted records."""
        events = db.scalars(select(ClinicalAuditEvent).order_by(ClinicalAuditEvent.id.asc())).all()

        expected_prev_hash = self.GENESIS_PREV_HASH
        broken_links_count = 0
        tampered_event_ids: list[str] = []
        chain_head: Optional[str] = None

        for event in events:
            # Check previous hash continuity
            if event.prev_record_hash != expected_prev_hash:
                broken_links_count += 1
                tampered_event_ids.append(event.event_id)

            # Re-calculate hash for this event
            computed_hash = ClinicalAuditEvent.calculate_hash(
                prev_hash=event.prev_record_hash,
                event_id=event.event_id,
                timestamp_iso=event.timestamp.isoformat() if event.timestamp else "",
                user_id=event.user_id,
                patient_id=event.patient_id,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                outcome=event.outcome,
            )

            if computed_hash != event.record_hash:
                broken_links_count += 1
                if event.event_id not in tampered_event_ids:
                    tampered_event_ids.append(event.event_id)

            expected_prev_hash = event.record_hash
            chain_head = event.record_hash

        tamper_detected = broken_links_count > 0
        status_str = "COMPROMISED" if tamper_detected else "VALID"

        return AuditIntegrityVerificationResponse(
            verified_at=datetime.now(timezone.utc),
            total_records_checked=len(events),
            tamper_detected=tamper_detected,
            broken_links_count=broken_links_count,
            tampered_event_ids=tampered_event_ids,
            chain_head_hash=chain_head,
            status=status_str,
        )

    def query_audit_events(
        self,
        db: Session,
        patient_id: Optional[str] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        outcome: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> AuditEventListResponse:
        """Query and paginate immutable clinical audit logs."""
        query = select(ClinicalAuditEvent)

        if patient_id:
            query = query.where(ClinicalAuditEvent.patient_id == patient_id)
        if user_id:
            query = query.where(ClinicalAuditEvent.user_id == user_id)
        if action:
            query = query.where(ClinicalAuditEvent.action == action)
        if resource_type:
            query = query.where(ClinicalAuditEvent.resource_type == resource_type)
        if outcome:
            query = query.where(ClinicalAuditEvent.outcome == outcome)
        if from_date:
            query = query.where(ClinicalAuditEvent.timestamp >= from_date)
        if to_date:
            query = query.where(ClinicalAuditEvent.timestamp <= to_date)

        total_count = db.scalar(select(func.count()).select_from(query.subquery())) or 0

        query = query.order_by(desc(ClinicalAuditEvent.id)).offset((page - 1) * page_size).limit(page_size)
        records = db.scalars(query).all()

        return AuditEventListResponse(
            events=[ClinicalAuditEventResponse.model_validate(r) for r in records],
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def get_audit_event_by_id(self, db: Session, event_id: str) -> Optional[ClinicalAuditEvent]:
        """Fetch audit event by unique event_id."""
        return db.scalars(
            select(ClinicalAuditEvent).where(ClinicalAuditEvent.event_id == event_id)
        ).first()


audit_service = AuditService()

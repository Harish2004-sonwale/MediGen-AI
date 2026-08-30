from collections import defaultdict
from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.security import (
    AuditAction,
    AuditOutcome,
    ClinicalAuditEvent,
    IncidentEventType,
    IncidentSeverity,
    IncidentStatus,
    SecurityIncident,
)
from app.models.user import User
from app.schemas.security import (
    SecurityIncidentCreateRequest,
    SecurityIncidentUpdateRequest,
    SecurityScanResult,
)
from app.services.audit_service import audit_service


class SecurityMonitoringService:
    """Proactive clinical security anomaly detection, threat monitoring, and incident triage."""

    def scan_and_detect_anomalies(
        self, db: Session, lookback_minutes: int = 60
    ) -> SecurityScanResult:
        """Scan recent audit logs to identify anomalous access patterns and spawn incidents."""
        cutoff_dt = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)

        events = db.scalars(
            select(ClinicalAuditEvent)
            .where(ClinicalAuditEvent.timestamp >= cutoff_dt)
            .order_by(ClinicalAuditEvent.timestamp.asc())
        ).all()

        created_incident_ids: list[str] = []

        # 1. Track cross-patient access by user
        user_patients: dict[int, set[str]] = defaultdict(set)
        user_failures: dict[int, int] = defaultdict(int)
        user_exports: dict[int, int] = defaultdict(int)
        ip_failures: dict[str, int] = defaultdict(int)

        for ev in events:
            if ev.user_id:
                if ev.patient_id and ev.user_role not in ["ADMIN", "admin"]:
                    user_patients[ev.user_id].add(ev.patient_id)

                if ev.outcome in [
                    AuditOutcome.DENIED_FORBIDDEN,
                    AuditOutcome.DENIED_NO_CONSENT,
                    AuditOutcome.ERROR,
                ]:
                    user_failures[ev.user_id] += 1

                if ev.action == AuditAction.EXPORT:
                    user_exports[ev.user_id] += 1

            if ev.ip_address and ev.outcome in [
                AuditOutcome.DENIED_FORBIDDEN,
                AuditOutcome.DENIED_NO_CONSENT,
                AuditOutcome.ERROR,
            ]:
                ip_failures[ev.ip_address] += 1

        # Heuristic 1: Cross-Patient Unauthorized Access Pattern (> 3 distinct patients in window)
        for user_id, patients in user_patients.items():
            if len(patients) >= 3:
                # Check if incident already open
                existing = db.scalars(
                    select(SecurityIncident).where(
                        SecurityIncident.user_id == user_id,
                        SecurityIncident.event_type == IncidentEventType.CROSS_PATIENT_ACCESS_ATTEMPT,
                        SecurityIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                    )
                ).first()
                if not existing:
                    incident = self._spawn_incident(
                        db=db,
                        severity=IncidentSeverity.HIGH,
                        event_type=IncidentEventType.CROSS_PATIENT_ACCESS_ATTEMPT,
                        user_id=user_id,
                        description=f"User accessed {len(patients)} distinct patient records within {lookback_minutes} minutes.",
                        evidence_metadata={
                            "patient_count": len(patients),
                            "lookback_minutes": lookback_minutes,
                            "patients_sampled": list(patients)[:5],
                        },
                    )
                    created_incident_ids.append(incident.incident_id)

        # Heuristic 2: Repeated Authorization / Access Failures (> 5 failures in window)
        for user_id, fail_count in user_failures.items():
            if fail_count >= 5:
                existing = db.scalars(
                    select(SecurityIncident).where(
                        SecurityIncident.user_id == user_id,
                        SecurityIncident.event_type == IncidentEventType.REPEATED_AUTH_FAILURE,
                        SecurityIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                    )
                ).first()
                if not existing:
                    incident = self._spawn_incident(
                        db=db,
                        severity=IncidentSeverity.MEDIUM,
                        event_type=IncidentEventType.REPEATED_AUTH_FAILURE,
                        user_id=user_id,
                        description=f"User encountered {fail_count} authorization/access failures within {lookback_minutes} minutes.",
                        evidence_metadata={"failure_count": fail_count, "lookback_minutes": lookback_minutes},
                    )
                    created_incident_ids.append(incident.incident_id)

        # Heuristic 3: Suspicious Bulk Export Pattern (> 3 exports in window)
        for user_id, export_count in user_exports.items():
            if export_count >= 3:
                existing = db.scalars(
                    select(SecurityIncident).where(
                        SecurityIncident.user_id == user_id,
                        SecurityIncident.event_type == IncidentEventType.SUSPICIOUS_BULK_EXPORT,
                        SecurityIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                    )
                ).first()
                if not existing:
                    incident = self._spawn_incident(
                        db=db,
                        severity=IncidentSeverity.HIGH,
                        event_type=IncidentEventType.SUSPICIOUS_BULK_EXPORT,
                        user_id=user_id,
                        description=f"User requested {export_count} bulk data exports within {lookback_minutes} minutes.",
                        evidence_metadata={"export_count": export_count, "lookback_minutes": lookback_minutes},
                    )
                    created_incident_ids.append(incident.incident_id)

        return SecurityScanResult(
            scanned_at=datetime.now(timezone.utc),
            events_analyzed=len(events),
            anomalies_detected=len(created_incident_ids),
            new_incidents_created=len(created_incident_ids),
            incident_ids=created_incident_ids,
        )

    def _spawn_incident(
        self,
        db: Session,
        severity: str,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        patient_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        evidence_metadata: Optional[dict] = None,
    ) -> SecurityIncident:
        """Internal helper to persist security incident and emit audit log."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        incident_id = f"SEC-{date_str}-{secrets.token_hex(6).upper()}"

        incident = SecurityIncident(
            incident_id=incident_id,
            detected_at=datetime.now(timezone.utc),
            severity=severity,
            status=IncidentStatus.OPEN,
            event_type=event_type,
            user_id=user_id,
            patient_id=patient_id,
            ip_address=ip_address,
            description=description,
            evidence_metadata=evidence_metadata or {},
        )

        db.add(incident)
        db.commit()
        db.refresh(incident)

        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            resource_type="SecurityIncident",
            resource_id=incident.incident_id,
            user_id=user_id,
            user_role="SYSTEM_SECURITY",
            patient_id=patient_id,
            outcome=AuditOutcome.WARNING,
            metadata={"severity": severity, "event_type": event_type, "incident_id": incident.incident_id},
        )

        return incident

    def create_incident(
        self,
        db: Session,
        request: SecurityIncidentCreateRequest,
        current_user: User,
    ) -> SecurityIncident:
        """Manually or programmatically register a triaged security incident."""
        return self._spawn_incident(
            db=db,
            severity=request.severity,
            event_type=request.event_type,
            description=request.description,
            user_id=request.user_id,
            patient_id=request.patient_id,
            ip_address=request.ip_address,
            evidence_metadata=request.evidence_metadata,
        )

    def update_incident(
        self,
        db: Session,
        incident_id: str,
        request: SecurityIncidentUpdateRequest,
        current_user: User,
    ) -> SecurityIncident:
        """Triage, assign, or resolve a security incident."""
        incident = db.scalars(
            select(SecurityIncident).where(SecurityIncident.incident_id == incident_id)
        ).first()
        if not incident:
            raise ValueError(f"Security incident '{incident_id}' not found")

        if request.status:
            incident.status = request.status
            if request.status in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]:
                incident.resolved_at = datetime.now(timezone.utc)
                incident.resolved_by_user_id = current_user.id

        if request.severity:
            incident.severity = request.severity

        if request.assigned_to_user_id is not None:
            incident.assigned_to_user_id = request.assigned_to_user_id

        if request.resolution_notes:
            incident.resolution_notes = request.resolution_notes

        db.commit()
        db.refresh(incident)

        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.UPDATE,
            resource_type="SecurityIncident",
            resource_id=incident.incident_id,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            outcome=AuditOutcome.SUCCESS,
            metadata={
                "status": incident.status,
                "severity": incident.severity,
                "assigned_to": incident.assigned_to_user_id,
            },
        )

        return incident

    def list_incidents(
        self,
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SecurityIncident], int]:
        """List and paginate security incidents."""
        query = select(SecurityIncident)
        if status:
            query = query.where(SecurityIncident.status == status)
        if severity:
            query = query.where(SecurityIncident.severity == severity)

        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        records = list(
            db.scalars(
                query.order_by(desc(SecurityIncident.detected_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return records, total

    def get_incident_by_id(self, db: Session, incident_id: str) -> Optional[SecurityIncident]:
        """Fetch security incident by ID."""
        return db.scalars(
            select(SecurityIncident).where(SecurityIncident.incident_id == incident_id)
        ).first()


security_monitoring_service = SecurityMonitoringService()

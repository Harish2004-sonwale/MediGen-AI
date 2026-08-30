from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.security import (
    AuditAction,
    AuditOutcome,
    ClinicalAuditEvent,
    ConsentStatus,
    DataRetentionPolicy,
    HoldStatus,
    IncidentSeverity,
    IncidentStatus,
    LegalClinicalHold,
    PatientConsent,
    SecurityIncident,
)
from app.models.user import User
from app.schemas.security import (
    ComplianceSummaryResponse,
    DataRetentionPolicyCreateRequest,
    LegalClinicalHoldCreateRequest,
    LegalClinicalHoldReleaseRequest,
)
from app.services.audit_service import audit_service


class ComplianceReportingService:
    """Clinical compliance governance, retention enforcement, legal holds, and reporting."""

    DEFAULT_POLICIES = [
        ("ADULT_EHR_7YR", "CLINICAL_ENCOUNTERS", 2555, "ARCHIVE", "Adult medical records retention policy (7 years)"),
        ("PEDIATRIC_EHR_21YR", "PEDIATRIC_RECORDS", 7665, "ARCHIVE", "Pediatric medical records retention policy (Age of majority + 3 years)"),
        ("AUDIT_LOG_6YR", "AUDIT_TRAIL", 2190, "RESTRICTED_ACCESS", "HIPAA security audit trail retention policy (6 years)"),
        ("IMAGING_10YR", "IMAGING_STUDIES", 3650, "ARCHIVE", "Radiology and diagnostic imaging studies retention (10 years)"),
        ("GENOMIC_PERMANENT", "GENOMICS", -1, "RESTRICTED_ACCESS", "Genomic profiles and precision oncology biomarkers (Permanent)"),
    ]

    def _ensure_default_policies(self, db: Session) -> None:
        """Seed default healthcare regulatory retention policies if not present."""
        for code, category, days, action, desc_text in self.DEFAULT_POLICIES:
            existing = db.scalars(
                select(DataRetentionPolicy).where(DataRetentionPolicy.policy_code == code)
            ).first()
            if not existing:
                policy = DataRetentionPolicy(
                    policy_code=code,
                    data_category=category,
                    retention_period_days=days,
                    action_on_expiry=action,
                    description=desc_text,
                    is_active=True,
                )
                db.add(policy)
        db.commit()

    def get_compliance_summary(self, db: Session) -> ComplianceSummaryResponse:
        """Calculate real-time system compliance score and security health metrics."""
        self._ensure_default_policies(db)

        now_dt = datetime.now(timezone.utc)
        last_24h_dt = now_dt - timedelta(hours=24)

        total_audit_events = db.scalar(select(func.count()).select_from(ClinicalAuditEvent)) or 0
        recent_audit_24h = (
            db.scalar(
                select(func.count()).select_from(ClinicalAuditEvent).where(ClinicalAuditEvent.timestamp >= last_24h_dt)
            )
            or 0
        )

        # Audit integrity check
        integrity_res = audit_service.verify_audit_trail_integrity(db)

        # Consent metrics
        total_active_consents = (
            db.scalar(
                select(func.count()).select_from(PatientConsent).where(PatientConsent.status == ConsentStatus.ACTIVE)
            )
            or 0
        )
        total_revoked_consents = (
            db.scalar(
                select(func.count()).select_from(PatientConsent).where(PatientConsent.status == ConsentStatus.REVOKED)
            )
            or 0
        )

        # Security incident metrics
        open_incidents = (
            db.scalar(
                select(func.count())
                .select_from(SecurityIncident)
                .where(SecurityIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]))
            )
            or 0
        )
        critical_incidents = (
            db.scalar(
                select(func.count())
                .select_from(SecurityIncident)
                .where(
                    SecurityIncident.severity == IncidentSeverity.CRITICAL,
                    SecurityIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                )
            )
            or 0
        )

        # Retention and holds
        active_holds = (
            db.scalar(
                select(func.count()).select_from(LegalClinicalHold).where(LegalClinicalHold.status == HoldStatus.ACTIVE)
            )
            or 0
        )
        active_policies = (
            db.scalar(
                select(func.count()).select_from(DataRetentionPolicy).where(DataRetentionPolicy.is_active == True)
            )
            or 0
        )

        # Compute compliance score (base 100)
        score = 100.0
        if integrity_res.tamper_detected:
            score -= 30.0
        if critical_incidents > 0:
            score -= min(30.0, critical_incidents * 10.0)
        if open_incidents > critical_incidents:
            score -= min(20.0, (open_incidents - critical_incidents) * 2.0)
        score = max(0.0, min(100.0, score))

        overall_status = "COMPLIANT" if score >= 85.0 else ("WARNING" if score >= 60.0 else "NON_COMPLIANT")

        return ComplianceSummaryResponse(
            generated_at=now_dt,
            total_audit_events=total_audit_events,
            recent_audit_events_24h=recent_audit_24h,
            audit_tamper_integrity_status=integrity_res.status,
            total_active_consents=total_active_consents,
            total_revoked_consents=total_revoked_consents,
            open_security_incidents=open_incidents,
            critical_security_incidents=critical_incidents,
            active_legal_holds=active_holds,
            active_retention_policies=active_policies,
            compliance_score_percent=round(score, 1),
            status=overall_status,
        )

    def list_retention_policies(self, db: Session) -> list[DataRetentionPolicy]:
        """List all active regulatory data retention policies."""
        self._ensure_default_policies(db)
        return list(db.scalars(select(DataRetentionPolicy).order_by(DataRetentionPolicy.id.asc())).all())

    def create_retention_policy(
        self,
        db: Session,
        request: DataRetentionPolicyCreateRequest,
        current_user: User,
    ) -> DataRetentionPolicy:
        """Create or update a regulatory retention schedule policy."""
        existing = db.scalars(
            select(DataRetentionPolicy).where(DataRetentionPolicy.policy_code == request.policy_code)
        ).first()

        if existing:
            existing.data_category = request.data_category
            existing.retention_period_days = request.retention_period_days
            existing.action_on_expiry = request.action_on_expiry
            existing.description = request.description
            existing.is_active = request.is_active
            policy = existing
        else:
            policy = DataRetentionPolicy(
                policy_code=request.policy_code,
                data_category=request.data_category,
                retention_period_days=request.retention_period_days,
                action_on_expiry=request.action_on_expiry,
                description=request.description,
                is_active=request.is_active,
            )
            db.add(policy)

        db.commit()
        db.refresh(policy)

        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.CREATE,
            resource_type="DataRetentionPolicy",
            resource_id=policy.policy_code,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            outcome=AuditOutcome.SUCCESS,
            metadata={"policy_code": policy.policy_code, "category": policy.data_category},
        )

        return policy

    def list_legal_holds(
        self,
        db: Session,
        status: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> list[LegalClinicalHold]:
        """List active or released clinical and legal holds."""
        query = select(LegalClinicalHold)
        if status:
            query = query.where(LegalClinicalHold.status == status)
        if patient_id:
            query = query.where(LegalClinicalHold.patient_id == patient_id)
        query = query.order_by(desc(LegalClinicalHold.placed_at))
        return list(db.scalars(query).all())

    def place_legal_hold(
        self,
        db: Session,
        request: LegalClinicalHoldCreateRequest,
        current_user: User,
    ) -> LegalClinicalHold:
        """Place an immutable legal/clinical hold on records."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        hold_id = f"HLD-{date_str}-{secrets.token_hex(6).upper()}"

        hold = LegalClinicalHold(
            hold_id=hold_id,
            patient_id=request.patient_id,
            scope_category=request.scope_category,
            reason=request.reason,
            status=HoldStatus.ACTIVE,
            placed_by_user_id=current_user.id,
            notes=request.notes,
        )

        db.add(hold)
        db.commit()
        db.refresh(hold)

        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.HOLD_APPLIED,
            resource_type="LegalClinicalHold",
            resource_id=hold.hold_id,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            patient_id=hold.patient_id,
            outcome=AuditOutcome.SUCCESS,
            metadata={"reason": hold.reason, "scope": hold.scope_category, "hold_id": hold.hold_id},
        )

        return hold

    def release_legal_hold(
        self,
        db: Session,
        hold_id: str,
        request: LegalClinicalHoldReleaseRequest,
        current_user: User,
    ) -> LegalClinicalHold:
        """Release an active legal/clinical hold."""
        hold = db.scalars(
            select(LegalClinicalHold).where(LegalClinicalHold.hold_id == hold_id)
        ).first()
        if not hold:
            raise ValueError(f"Legal hold '{hold_id}' not found")

        if hold.status == HoldStatus.RELEASED:
            return hold

        hold.status = HoldStatus.RELEASED
        hold.released_by_user_id = current_user.id
        hold.released_at = datetime.now(timezone.utc)
        if request.notes:
            hold.notes = f"{hold.notes or ''}\nRelease Note: {request.notes}".strip()

        db.commit()
        db.refresh(hold)

        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.HOLD_RELEASED,
            resource_type="LegalClinicalHold",
            resource_id=hold.hold_id,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            patient_id=hold.patient_id,
            outcome=AuditOutcome.SUCCESS,
            metadata={"release_notes": request.notes, "hold_id": hold.hold_id},
        )

        return hold


compliance_reporting_service = ComplianceReportingService()

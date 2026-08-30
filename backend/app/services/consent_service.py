from datetime import datetime, timezone
import secrets
from typing import Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.security import (
    AuditAction,
    AuditOutcome,
    ConsentPolicyRule,
    ConsentScope,
    ConsentStatus,
    PatientConsent,
)
from app.models.user import User
from app.schemas.security import (
    ConsentVerificationRequest,
    ConsentVerificationResponse,
    PatientConsentCreateRequest,
    PatientConsentRevokeRequest,
)
from app.services.audit_service import audit_service


class ConsentService:
    """Patient consent lifecycle management, policy evaluation, and digital signature verification."""

    def _resolve_patient(self, db: Session, patient_id_str: str) -> Patient:
        """Resolve patient record by patient_id or raise ValueError."""
        patient = db.scalars(
            select(Patient).where(
                (Patient.patient_id == patient_id_str)
                | (Patient.id == (int(patient_id_str) if patient_id_str.isdigit() else -1))
            )
        ).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id_str}' not found")
        return patient

    def grant_consent(
        self,
        db: Session,
        patient_id_str: str,
        request: PatientConsentCreateRequest,
        current_user: User,
    ) -> PatientConsent:
        """Grant and persist a new patient consent directive with digital signature hashing."""
        patient = self._resolve_patient(db, patient_id_str)

        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        consent_id = f"CNS-{date_str}-{secrets.token_hex(6).upper()}"
        valid_from = request.valid_from or datetime.now(timezone.utc)

        # Compute SHA-256 digital signature hash
        signature_hash = PatientConsent.compute_signature_hash(
            patient_id=patient.patient_id,
            scope=request.scope,
            policy_rule=request.policy_rule,
            purpose_of_use=request.purpose_of_use,
            signer_name=request.signer_name,
            valid_from_iso=valid_from.isoformat(),
        )

        consent = PatientConsent(
            consent_id=consent_id,
            patient_id=patient.patient_id,
            status=ConsentStatus.ACTIVE,
            scope=request.scope,
            policy_rule=request.policy_rule,
            purpose_of_use=request.purpose_of_use,
            data_category=request.data_category,
            actor_type=request.actor_type,
            actor_reference=request.actor_reference,
            valid_from=valid_from,
            valid_to=request.valid_to,
            signed_by_patient=request.signed_by_patient,
            signer_name=request.signer_name,
            signer_relationship=request.signer_relationship,
            witness_or_clinician_id=request.witness_or_clinician_id or current_user.id,
            digital_signature_hash=signature_hash,
        )

        db.add(consent)
        db.commit()
        db.refresh(consent)

        # Emit audit event
        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.CONSENT_GRANT,
            resource_type="PatientConsent",
            resource_id=consent.consent_id,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            patient_id=patient.patient_id,
            purpose_of_use=request.purpose_of_use,
            outcome=AuditOutcome.SUCCESS,
            metadata={
                "scope": consent.scope,
                "policy_rule": consent.policy_rule,
                "signer_name": consent.signer_name,
                "digital_signature_hash": consent.digital_signature_hash,
            },
        )

        return consent

    def revoke_consent(
        self,
        db: Session,
        consent_id: str,
        request: PatientConsentRevokeRequest,
        current_user: User,
    ) -> PatientConsent:
        """Immediately revoke an active consent directive."""
        consent = db.scalars(
            select(PatientConsent).where(PatientConsent.consent_id == consent_id)
        ).first()
        if not consent:
            raise ValueError(f"Consent directive '{consent_id}' not found")

        if consent.status == ConsentStatus.REVOKED:
            return consent

        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.now(timezone.utc)
        consent.revocation_reason = request.revocation_reason
        consent.revoked_by_user_id = current_user.id

        db.commit()
        db.refresh(consent)

        # Emit audit event
        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.CONSENT_REVOKE,
            resource_type="PatientConsent",
            resource_id=consent.consent_id,
            user_id=current_user.id,
            user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            patient_id=consent.patient_id,
            purpose_of_use=consent.purpose_of_use,
            outcome=AuditOutcome.SUCCESS,
            metadata={
                "revocation_reason": consent.revocation_reason,
                "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
            },
        )

        return consent

    def verify_consent(
        self,
        db: Session,
        request: ConsentVerificationRequest,
        current_user: Optional[User] = None,
    ) -> ConsentVerificationResponse:
        """Evaluate active patient consent policies against requested clinical operation."""
        patient = self._resolve_patient(db, request.patient_id)
        now_dt = datetime.now(timezone.utc)

        # Emergency override check
        if request.purpose_of_use.upper() == "EMERGENCY_OVERRIDE":
            if current_user:
                audit_service.emit_audit_event(
                    db=db,
                    action=AuditAction.READ,
                    resource_type=request.resource_type,
                    resource_id=None,
                    user_id=current_user.id,
                    user_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
                    patient_id=patient.patient_id,
                    purpose_of_use="EMERGENCY_OVERRIDE",
                    outcome=AuditOutcome.SUCCESS,
                    metadata={"reason": "Emergency medical treatment override invoked"},
                )
            return ConsentVerificationResponse(
                patient_id=patient.patient_id,
                resource_type=request.resource_type,
                action=request.action,
                purpose_of_use=request.purpose_of_use,
                is_permitted=True,
                reason="Permitted under emergency clinical override protocol",
                is_emergency_override=True,
            )

        # Fetch active consents for patient
        consents = db.scalars(
            select(PatientConsent)
            .where(
                PatientConsent.patient_id == patient.patient_id,
                PatientConsent.status == ConsentStatus.ACTIVE,
            )
            .order_by(desc(PatientConsent.id))
        ).all()

        # Check for explicit DENY rules
        for c in consents:
            # Check expiration
            if c.valid_to and c.valid_to < now_dt:
                continue

            if c.policy_rule == ConsentPolicyRule.DENY:
                # If category matches or scope covers this
                if c.scope == ConsentScope.ALL_RECORDS:
                    return ConsentVerificationResponse(
                        patient_id=patient.patient_id,
                        resource_type=request.resource_type,
                        action=request.action,
                        purpose_of_use=request.purpose_of_use,
                        is_permitted=False,
                        reason=f"Blocked by active global DENY consent directive ({c.consent_id})",
                        matched_consent_id=c.consent_id,
                    )
                if request.data_category and c.data_category and request.data_category.upper() == c.data_category.upper():
                    return ConsentVerificationResponse(
                        patient_id=patient.patient_id,
                        resource_type=request.resource_type,
                        action=request.action,
                        purpose_of_use=request.purpose_of_use,
                        is_permitted=False,
                        reason=f"Blocked by explicit category-specific DENY consent directive ({c.consent_id})",
                        matched_consent_id=c.consent_id,
                    )
                if request.action == "EXPORT" and c.scope == ConsentScope.RESTRICT_EXPORT:
                    return ConsentVerificationResponse(
                        patient_id=patient.patient_id,
                        resource_type=request.resource_type,
                        action=request.action,
                        purpose_of_use=request.purpose_of_use,
                        is_permitted=False,
                        reason=f"Blocked by explicit RESTRICT_EXPORT consent directive ({c.consent_id})",
                        matched_consent_id=c.consent_id,
                    )

        # Check if research or 3rd party disclosure requires explicit permit
        if request.purpose_of_use.upper() in ["RESEARCH", "THIRD_PARTY_SHARING"]:
            permit_found = False
            permit_id = None
            for c in consents:
                if c.valid_to and c.valid_to < now_dt:
                    continue
                if c.policy_rule == ConsentPolicyRule.PERMIT:
                    if c.purpose_of_use.upper() == request.purpose_of_use.upper() or c.scope in [
                        ConsentScope.RESEARCH_ONLY,
                        ConsentScope.ALL_RECORDS,
                    ]:
                        permit_found = True
                        permit_id = c.consent_id
                        break
            if not permit_found:
                return ConsentVerificationResponse(
                    patient_id=patient.patient_id,
                    resource_type=request.resource_type,
                    action=request.action,
                    purpose_of_use=request.purpose_of_use,
                    is_permitted=False,
                    reason=f"Operation requires explicit patient PERMIT consent directive for '{request.purpose_of_use}'",
                )
            return ConsentVerificationResponse(
                patient_id=patient.patient_id,
                resource_type=request.resource_type,
                action=request.action,
                purpose_of_use=request.purpose_of_use,
                is_permitted=True,
                reason="Permitted by active explicit patient research/disclosure consent directive",
                matched_consent_id=permit_id,
            )

        # Standard treatment care team access allowed
        return ConsentVerificationResponse(
            patient_id=patient.patient_id,
            resource_type=request.resource_type,
            action=request.action,
            purpose_of_use=request.purpose_of_use,
            is_permitted=True,
            reason="Permitted under standard treatment care team authorization",
        )

    def list_patient_consents(
        self,
        db: Session,
        patient_id_str: str,
        status: Optional[str] = None,
    ) -> list[PatientConsent]:
        """List chronological consent directives for a patient."""
        patient = self._resolve_patient(db, patient_id_str)
        query = select(PatientConsent).where(PatientConsent.patient_id == patient.patient_id)
        if status:
            query = query.where(PatientConsent.status == status)
        query = query.order_by(desc(PatientConsent.id))
        return list(db.scalars(query).all())

    def get_consent_by_id(self, db: Session, consent_id: str) -> Optional[PatientConsent]:
        """Retrieve consent directive by consent_id."""
        return db.scalars(
            select(PatientConsent).where(PatientConsent.consent_id == consent_id)
        ).first()


consent_service = ConsentService()

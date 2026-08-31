"""Tenant Context Resolution and Query Isolation Utilities."""

from contextvars import ContextVar
from typing import Optional, TypeVar
from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Query, Session

from app.models.security import AuditAction, AuditOutcome
from app.models.tenant import ClinicalFacility
from app.models.user import User, UserRole
from app.services.audit_service import audit_service

_current_facility_context: ContextVar[Optional[str]] = ContextVar("current_facility_context", default=None)

T = TypeVar("T")


def get_current_facility_id() -> Optional[str]:
    """Return the facility_id for the active request execution context."""
    return _current_facility_context.get()


def set_current_facility_id(facility_id: Optional[str]) -> None:
    """Set the facility_id for the active request execution context."""
    _current_facility_context.set(facility_id)


def resolve_facility_id(
    request: Request,
    x_facility_id: Optional[str] = Header(None, alias="X-Facility-ID"),
) -> str:
    """FastAPI Dependency resolving the target clinical facility ID from request headers or user context."""
    if x_facility_id and x_facility_id.strip():
        facility_id = x_facility_id.strip()
        set_current_facility_id(facility_id)
        return facility_id

    # Fallback to default enterprise facility if not specified
    fallback = "FAC-001"
    set_current_facility_id(fallback)
    return fallback


def apply_tenant_filter(query: Query[T], model_cls: type[T], facility_id: Optional[str] = None) -> Query[T]:
    """Helper to safely filter queries by facility_id if the model possesses tenant isolation."""
    target_facility = facility_id or get_current_facility_id()
    if target_facility and hasattr(model_cls, "facility_id"):
        return query.filter(
            (getattr(model_cls, "facility_id") == target_facility)
            | (getattr(model_cls, "facility_id").is_(None))
        )
    return query


def verify_cross_facility_transfer_authorization(
    db: Session,
    user: User,
    source_facility_id: Optional[str],
    destination_facility_id: Optional[str],
    patient_id: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> bool:
    """Verifies clinician authorization for cross-facility patient transfer/referral and records audit events."""
    # A. SAME-FACILITY: If source == destination (or not cross-facility), preserve existing behavior
    if not source_facility_id or not destination_facility_id or source_facility_id == destination_facility_id:
        return True

    # B. CROSS-FACILITY: If source != destination
    # 1. Verify source facility exists and is active
    src_fac = db.query(ClinicalFacility).filter(
        ClinicalFacility.facility_id == source_facility_id,
        ClinicalFacility.is_active == True,  # noqa: E712
    ).first()
    if not src_fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source facility '{source_facility_id}' not found or inactive.",
        )

    # 2. Verify destination facility exists and is active
    dest_fac = db.query(ClinicalFacility).filter(
        ClinicalFacility.facility_id == destination_facility_id,
        ClinicalFacility.is_active == True,  # noqa: E712
    ).first()
    if not dest_fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination facility '{destination_facility_id}' not found or inactive.",
        )

    # 3. Verify user privileges in source facility
    is_admin = user.role == UserRole.ADMIN or (hasattr(user.role, "value") and user.role.value == "admin")
    user_facility = getattr(user, "default_facility_id", None) or "FAC-001"

    if not is_admin and user_facility != source_facility_id:
        # Audit denied attempt
        try:
            audit_service.emit_audit_event(
                db=db,
                action=AuditAction.CROSS_FACILITY_TRANSFER,
                resource_type="ClinicalHandoff",
                resource_id=resource_id,
                user_id=user.id,
                user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                patient_id=patient_id,
                purpose_of_use="TRANSFER_OF_CARE",
                outcome=AuditOutcome.DENIED_FORBIDDEN,
                metadata={
                    "source_facility_id": source_facility_id,
                    "destination_facility_id": destination_facility_id,
                    "attempted_by_user_id": user.id,
                    "reason": f"Clinician does not possess active clinical privileges at source facility '{source_facility_id}'.",
                },
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Clinician does not possess active clinical privileges at source facility.",
        )

    # 4. Authorized cross-facility transfer: Emit dedicated audit event
    try:
        audit_service.emit_audit_event(
            db=db,
            action=AuditAction.CROSS_FACILITY_TRANSFER,
            resource_type="ClinicalHandoff",
            resource_id=resource_id,
            user_id=user.id,
            user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            patient_id=patient_id,
            purpose_of_use="TRANSFER_OF_CARE",
            outcome=AuditOutcome.SUCCESS,
            metadata={
                "source_facility_id": source_facility_id,
                "destination_facility_id": destination_facility_id,
                "authorized_by_user_id": user.id,
                "operation": "CROSS_FACILITY_TRANSFER",
            },
        )
    except Exception:
        pass

    return True

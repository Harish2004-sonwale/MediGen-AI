"""Tenant Context Resolution and Query Isolation Utilities."""

from contextvars import ContextVar
from typing import Optional, TypeVar
from fastapi import Header, Request
from sqlalchemy.orm import Query, Session

from app.models.tenant import ClinicalFacility

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

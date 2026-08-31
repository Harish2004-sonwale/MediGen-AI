"""API Endpoints for HL7 FHIR R4 Topic Subscriptions."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.fhir_subscription import (
    FHIRSubscriptionCreate,
    FHIRSubscriptionResponse,
    FHIRSubscriptionUpdate,
)
from app.schemas.user import UserRole
from app.services import fhir_subscription_service

router = APIRouter(prefix="/fhir/Subscription", tags=["FHIR R4 Subscriptions"])


@router.post("", response_model=FHIRSubscriptionResponse, status_code=status.HTTP_201_CREATED, summary="Create FHIR Subscription")
def create_subscription(
    payload: FHIRSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> FHIRSubscriptionResponse:
    """Create and register a new topic-based webhook or websocket subscription."""
    return fhir_subscription_service.create_fhir_subscription(db, payload)


@router.get("", response_model=List[FHIRSubscriptionResponse], summary="List FHIR Subscriptions")
def list_subscriptions(
    facility_id: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[FHIRSubscriptionResponse]:
    """List active topic subscriptions."""
    return fhir_subscription_service.list_fhir_subscriptions(db, facility_id=facility_id, topic=topic)


@router.get("/{subscription_id}", response_model=FHIRSubscriptionResponse, summary="Get FHIR Subscription Details")
def get_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FHIRSubscriptionResponse:
    """Get subscription by ID."""
    sub = fhir_subscription_service.get_fhir_subscription(db, subscription_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return sub


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete FHIR Subscription")
def delete_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    """Unsubscribe and delete topic subscription."""
    deleted = fhir_subscription_service.delete_fhir_subscription(db, subscription_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

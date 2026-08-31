"""API Endpoints for HL7 CDS Hooks Specification v2.0."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cds import (
    CDSHookRequest,
    CDSHookResponse,
    CDSServicesDiscoveryResponse,
)
from app.services.cds_hooks_service import cds_hooks_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=CDSServicesDiscoveryResponse, summary="CDS Services Discovery Endpoint")
def get_cds_services() -> CDSServicesDiscoveryResponse:
    """Returns the catalogue of all available CDS Services."""
    return cds_hooks_service.get_services_discovery()


@router.post("/patient-view", response_model=CDSHookResponse, summary="CDS Hook: patient-view")
def invoke_patient_view(
    request: CDSHookRequest,
    db: Session = Depends(get_db),
) -> CDSHookResponse:
    """Evaluates patient chart on opening and returns care gaps, active alerts and advice."""
    return cds_hooks_service.handle_hook(db=db, request=request)


@router.post("/order-select", response_model=CDSHookResponse, summary="CDS Hook: order-select")
def invoke_order_select(
    request: CDSHookRequest,
    db: Session = Depends(get_db),
) -> CDSHookResponse:
    """Evaluates draft orders for drug-drug interactions, allergies and contraindications."""
    return cds_hooks_service.handle_hook(db=db, request=request)


@router.post("/order-sign", response_model=CDSHookResponse, summary="CDS Hook: order-sign")
def invoke_order_sign(
    request: CDSHookRequest,
    db: Session = Depends(get_db),
) -> CDSHookResponse:
    """Evaluates final diagnostic and medication orders before clinical signature."""
    return cds_hooks_service.handle_hook(db=db, request=request)


@router.post("/appointment-book", response_model=CDSHookResponse, summary="CDS Hook: appointment-book")
def invoke_appointment_book(
    request: CDSHookRequest,
    db: Session = Depends(get_db),
) -> CDSHookResponse:
    """Evaluates department scheduling and provider conflicts during appointment booking."""
    return cds_hooks_service.handle_hook(db=db, request=request)

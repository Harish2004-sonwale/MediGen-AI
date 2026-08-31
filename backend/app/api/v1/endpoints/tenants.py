"""API Endpoints for Multi-Tenant Health Systems, Facilities and Departments."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tenant import (
    ClinicalFacilityCreate,
    ClinicalFacilityResponse,
    DepartmentUnitCreate,
    DepartmentUnitResponse,
    EHRIntegrationConfigCreate,
    EHRIntegrationConfigResponse,
    HealthOrganizationCreate,
    HealthOrganizationResponse,
)
from app.services.tenant_service import tenant_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/organizations", response_model=List[HealthOrganizationResponse], summary="List Health Organizations")
def list_organizations(db: Session = Depends(get_db)) -> List[HealthOrganizationResponse]:
    return tenant_service.list_organizations(db=db)


@router.post("/organizations", response_model=HealthOrganizationResponse, summary="Create Health Organization")
def create_organization(
    payload: HealthOrganizationCreate,
    db: Session = Depends(get_db),
) -> HealthOrganizationResponse:
    return tenant_service.create_organization(db=db, payload=payload)


@router.get("/facilities", response_model=List[ClinicalFacilityResponse], summary="List Clinical Facilities")
def list_facilities(
    org_id: Optional[str] = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db),
) -> List[ClinicalFacilityResponse]:
    return tenant_service.list_facilities(db=db, org_id=org_id)


@router.post("/facilities", response_model=ClinicalFacilityResponse, summary="Create Clinical Facility")
def create_facility(
    payload: ClinicalFacilityCreate,
    db: Session = Depends(get_db),
) -> ClinicalFacilityResponse:
    return tenant_service.create_facility(db=db, payload=payload)


@router.get("/facilities/{facility_id}/departments", response_model=List[DepartmentUnitResponse], summary="List Facility Departments")
def list_facility_departments(
    facility_id: str,
    db: Session = Depends(get_db),
) -> List[DepartmentUnitResponse]:
    return tenant_service.list_departments(db=db, facility_id=facility_id)


@router.post("/departments", response_model=DepartmentUnitResponse, summary="Create Department Unit")
def create_department(
    payload: DepartmentUnitCreate,
    db: Session = Depends(get_db),
) -> DepartmentUnitResponse:
    return tenant_service.create_department(db=db, payload=payload)


@router.get("/facilities/{facility_id}/ehr-config", response_model=Optional[EHRIntegrationConfigResponse], summary="Get Facility EHR Config")
def get_facility_ehr_config(
    facility_id: str,
    db: Session = Depends(get_db),
) -> Optional[EHRIntegrationConfigResponse]:
    return tenant_service.get_facility_ehr_config(db=db, facility_id=facility_id)


@router.post("/ehr-config", response_model=EHRIntegrationConfigResponse, summary="Configure Facility EHR Integration")
def configure_facility_ehr(
    payload: EHRIntegrationConfigCreate,
    db: Session = Depends(get_db),
) -> EHRIntegrationConfigResponse:
    return tenant_service.configure_ehr_integration(db=db, payload=payload)

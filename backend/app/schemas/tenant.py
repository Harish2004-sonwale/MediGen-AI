"""Pydantic schemas for Multi-Tenant Health Organizations, Facilities and Departments."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DepartmentUnitBase(BaseModel):
    name: str = Field(..., description="Department name, e.g., Cardiology ICU")
    dept_code: str = Field(..., description="Department code, e.g., CICU-01")
    floor_or_wing: Optional[str] = Field(None, description="Floor or wing location")
    is_active: bool = True


class DepartmentUnitCreate(DepartmentUnitBase):
    department_id: Optional[str] = None
    facility_id: str


class DepartmentUnitResponse(DepartmentUnitBase):
    id: int
    department_id: str
    facility_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClinicalFacilityBase(BaseModel):
    name: str = Field(..., description="Facility name, e.g., St. Jude Memorial Hospital")
    facility_code: str = Field(..., description="Unique facility code, e.g., SJM-01")
    address_json: Dict[str, Any] = Field(default_factory=dict, description="Address metadata")
    is_active: bool = True


class ClinicalFacilityCreate(ClinicalFacilityBase):
    facility_id: Optional[str] = None
    org_id: str


class ClinicalFacilityResponse(ClinicalFacilityBase):
    id: int
    facility_id: str
    org_id: str
    created_at: datetime
    updated_at: datetime
    departments: List[DepartmentUnitResponse] = []

    class Config:
        from_attributes = True


class HealthOrganizationBase(BaseModel):
    name: str = Field(..., description="Organization name, e.g., Metropolitan Health System")
    org_type: str = Field(default="HOSPITAL_NETWORK", description="Type: HOSPITAL_NETWORK, ACO, AMBULATORY_GROUP")
    is_active: bool = True


class HealthOrganizationCreate(HealthOrganizationBase):
    org_id: Optional[str] = None


class HealthOrganizationResponse(HealthOrganizationBase):
    id: int
    org_id: str
    created_at: datetime
    updated_at: datetime
    facilities: List[ClinicalFacilityResponse] = []

    class Config:
        from_attributes = True


class EHRIntegrationConfigBase(BaseModel):
    ehr_vendor: str = Field(default="EPIC", description="Vendor: EPIC, CERNER, ATHENAHEALTH, GENERIC_FHIR")
    fhir_base_url: str = Field(..., description="Base URL of the EHR FHIR server")
    client_id: str = Field(..., description="OAuth2 Client ID registered with EHR")
    smart_auth_url: Optional[str] = None
    smart_token_url: Optional[str] = None
    is_enabled: bool = True


class EHRIntegrationConfigCreate(EHRIntegrationConfigBase):
    config_id: Optional[str] = None
    facility_id: str


class EHRIntegrationConfigResponse(EHRIntegrationConfigBase):
    id: int
    config_id: str
    facility_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

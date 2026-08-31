"""Unit & Integration Tests for Multi-Tenant Health Systems, Facilities and Departments."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.models.tenant import ClinicalFacility, DepartmentUnit, HealthOrganization
from app.models.user import User
from app.services.tenant_service import tenant_service


def test_create_and_list_health_organizations(client: TestClient, db_session: Session):
    """Verifies creation and listing of top-level health system organizations."""
    resp = client.post(
        "/api/v1/tenants/organizations",
        json={
            "name": "Metropolitan Regional Health System",
            "org_type": "HOSPITAL_NETWORK",
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Metropolitan Regional Health System"
    assert "org_id" in data

    list_resp = client.get("/api/v1/tenants/organizations")
    assert list_resp.status_code == 200
    orgs = list_resp.json()
    assert len(orgs) >= 1
    assert any(o["name"] == "Metropolitan Regional Health System" for o in orgs)


def test_create_clinical_facility_and_departments(client: TestClient, db_session: Session):
    """Verifies facility creation and department unit isolation."""
    # 1. Create Org
    org_resp = client.post(
        "/api/v1/tenants/organizations",
        json={"name": "St. Jude Health Network", "org_type": "HOSPITAL_NETWORK"},
    )
    org_id = org_resp.json()["org_id"]

    # 2. Create Facility
    fac_resp = client.post(
        "/api/v1/tenants/facilities",
        json={
            "org_id": org_id,
            "name": "St. Jude Memorial Hospital",
            "facility_code": "SJM-NORTH-01",
            "address_json": {"city": "Boston", "state": "MA", "zip": "02115"},
        },
    )
    assert fac_resp.status_code == 200
    fac_data = fac_resp.json()
    facility_id = fac_data["facility_id"]
    assert fac_data["name"] == "St. Jude Memorial Hospital"

    # 3. Create Department
    dept_resp = client.post(
        "/api/v1/tenants/departments",
        json={
            "facility_id": facility_id,
            "name": "Cardiovascular Intensive Care Unit",
            "dept_code": "CICU-3A",
            "floor_or_wing": "Tower 3, Floor 4",
        },
    )
    assert dept_resp.status_code == 200
    dept_data = dept_resp.json()
    assert dept_data["dept_code"] == "CICU-3A"

    # 4. List Departments
    list_dept = client.get(f"/api/v1/tenants/facilities/{facility_id}/departments")
    assert list_dept.status_code == 200
    depts = list_dept.json()
    assert len(depts) >= 1
    assert depts[0]["dept_code"] == "CICU-3A"


def test_ehr_integration_config(client: TestClient, db_session: Session):
    """Verifies configuration of EHR integration settings per facility."""
    org_resp = client.post(
        "/api/v1/tenants/organizations",
        json={"name": "Apex Healthcare Partners"},
    )
    org_id = org_resp.json()["org_id"]

    fac_resp = client.post(
        "/api/v1/tenants/facilities",
        json={
            "org_id": org_id,
            "name": "Apex Central Pavilion",
            "facility_code": "APEX-CENTRAL-01",
        },
    )
    facility_id = fac_resp.json()["facility_id"]

    # Configure EHR
    ehr_resp = client.post(
        "/api/v1/tenants/ehr-config",
        json={
            "facility_id": facility_id,
            "ehr_vendor": "EPIC",
            "fhir_base_url": "https://epic-fhir.apexhealth.org/api/FHIR/R4",
            "client_id": "apex-epic-client-id-001",
            "smart_auth_url": "https://epic-fhir.apexhealth.org/oauth2/authorize",
            "smart_token_url": "https://epic-fhir.apexhealth.org/oauth2/token",
            "is_enabled": True,
        },
    )
    assert ehr_resp.status_code == 200
    ehr_data = ehr_resp.json()
    assert ehr_data["ehr_vendor"] == "EPIC"
    assert ehr_data["client_id"] == "apex-epic-client-id-001"

    # Retrieve EHR Config
    get_ehr = client.get(f"/api/v1/tenants/facilities/{facility_id}/ehr-config")
    assert get_ehr.status_code == 200
    assert get_ehr.json()["ehr_vendor"] == "EPIC"


def test_tenant_security_facility_access_guard(db_session: Session):
    """Verifies tenant security boundary checks and emergency override logic."""
    doctor = User(id=999, email="dr.smith@hospital.org", role="doctor", is_active=True)
    admin = User(id=998, email="admin@hospital.org", role="admin", is_active=True)

    # Admin access
    assert tenant_service.check_user_facility_access(admin, "FAC-TARGET-01") is True

    # Emergency purpose of use override
    assert tenant_service.check_user_facility_access(doctor, "FAC-TARGET-01", purpose_of_use="EMERGENCY") is True

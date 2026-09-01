"""Unit and Integration Tests for Regional Multi-Hospital Clinical Pathways & Care Plan Synchronization."""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.outbox import OutboxEvent
from app.models.patient import Patient
from app.models.tenant import ClinicalFacility, HealthOrganization
from app.schemas.patient import Gender, PatientStatus
from app.schemas.pathway import (
    PathwayMilestoneCreate,
    PathwayStageCreate,
    RegionalPathwayCreate,
)
from app.services.pathway_service import pathway_service


@pytest.fixture
def pathway_test_setup(db_session: Session):
    """Set up facilities, a patient, and a multi-stage clinical pathway."""
    org = HealthOrganization(org_id="ORG-TEST-01", name="Regional Health Network")
    fac1 = ClinicalFacility(facility_id="FAC-001", org_id="ORG-TEST-01", name="Metro Main", facility_code="MM-01", is_active=True)
    fac2 = ClinicalFacility(facility_id="FAC-002", org_id="ORG-TEST-01", name="West Community", facility_code="WC-02", is_active=True)
    db_session.add_all([org, fac1, fac2])
    db_session.flush()

    patient = Patient(
        patient_id="PAT-PATH-001",
        first_name="George",
        last_name="Washington",
        date_of_birth=date(1972, 2, 22),
        gender=Gender.MALE,
        email="george.w@example.com",
        phone="+1-555-0155",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-001",
    )
    db_session.add(patient)
    db_session.commit()

    # Create Regional STEMI Pathway
    pathway_res = pathway_service.create_pathway(
        db=db_session,
        pathway_in=RegionalPathwayCreate(
            code="STEMI_FAST_TRACK",
            name="Regional STEMI Door-to-Balloon Protocol",
            category="cardiology",
            description="Multi-facility rapid reperfusion protocol.",
            target_duration_hours=12,
            stages=[
                PathwayStageCreate(
                    sequence_order=1,
                    name="Community ED Triage & 12-Lead ECG",
                    assigned_facility_id="FAC-001",
                    target_duration_minutes=30,
                    milestones=[
                        PathwayMilestoneCreate(name="Diagnostic ECG within 10 min", criteria_code="ECG-10MIN", is_critical=True),
                        PathwayMilestoneCreate(name="Aspirin 325mg PO chewed", criteria_code="MED-ASA-325", is_critical=True),
                    ],
                ),
                PathwayStageCreate(
                    sequence_order=2,
                    name="Emergency Transfer to Cath Lab Hub",
                    assigned_facility_id="FAC-002",
                    target_duration_minutes=60,
                    milestones=[
                        PathwayMilestoneCreate(name="Percutaneous Coronary Intervention", criteria_code="PROC-PCI", is_critical=True),
                    ],
                ),
                PathwayStageCreate(
                    sequence_order=3,
                    name="Cardiac ICU Recovery",
                    assigned_facility_id="FAC-002",
                    target_duration_minutes=720,
                    milestones=[
                        PathwayMilestoneCreate(name="Post-PCI Heparin Protocol", criteria_code="MED-HEPARIN", is_critical=False),
                    ],
                ),
            ],
        ),
        user_id=1,
    )
    return patient, pathway_res


def test_pathway_definition_lifecycle(db_session, pathway_test_setup):
    """Verify pathway creation with ordered stages and milestones."""
    _, pathway = pathway_test_setup
    assert pathway.code == "STEMI_FAST_TRACK"
    assert len(pathway.stages) == 3
    assert pathway.stages[0].name == "Community ED Triage & 12-Lead ECG"
    assert len(pathway.stages[0].milestones) == 2


def test_patient_enrollment_and_progression(db_session, pathway_test_setup, test_doctor_user):
    """Verify patient enrollment, stage transitions, milestone completion, and outbox event dispatch."""
    patient, pathway = pathway_test_setup

    # 1. Enroll
    enrollment = pathway_service.enroll_patient(
        db=db_session,
        patient_id=patient.patient_id,
        pathway_id=pathway.pathway_id,
        user=test_doctor_user,
        facility_id="FAC-001",
    )
    assert enrollment.enrollment_id.startswith("ENR-")
    assert enrollment.status == "active"
    assert enrollment.current_stage_id == pathway.stages[0].stage_id

    # 2. Complete Milestone
    ms_id = pathway.stages[0].milestones[0].milestone_id
    updated_enr = pathway_service.complete_milestone(
        db=db_session,
        enrollment_id=enrollment.enrollment_id,
        milestone_id=ms_id,
        user=test_doctor_user,
    )
    assert ms_id in updated_enr.completed_milestones

    # 3. Advance to Stage 2 (Transfers from FAC-001 to FAC-002)
    advanced_enr = pathway_service.advance_stage(
        db=db_session,
        enrollment_id=enrollment.enrollment_id,
        user=test_doctor_user,
    )
    assert advanced_enr.current_stage_id == pathway.stages[1].stage_id
    assert advanced_enr.facility_id == "FAC-002"

    # Check outbox events emitted
    outbox_events = db_session.query(OutboxEvent).filter(
        OutboxEvent.aggregate_id == enrollment.enrollment_id
    ).all()
    event_types = [e.event_type for e in outbox_events]
    assert "REGIONAL_PATHWAY_ENROLLED" in event_types
    assert "REGIONAL_PATHWAY_STAGE_TRANSITION" in event_types


def test_pathway_endpoints(client: TestClient, db_session: Session, pathway_test_setup, test_doctor_user):
    """Test pathway API endpoints."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_doctor_user.id, role=test_doctor_user.role.value)
    headers = {"Authorization": f"Bearer {token}", "X-Facility-ID": "FAC-001"}

    patient, pathway = pathway_test_setup

    # 1. List pathways
    list_resp = client.get("/api/v1/pathways", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 2. Enroll patient
    enr_resp = client.post(
        "/api/v1/pathways/enroll",
        headers=headers,
        json={
            "patient_id": patient.patient_id,
            "pathway_id": pathway.pathway_id,
        },
    )
    assert enr_resp.status_code == 201
    enr_data = enr_resp.json()
    enrollment_id = enr_data["enrollment_id"]

    # 3. Complete milestone
    ms_id = pathway.stages[0].milestones[0].milestone_id
    ms_resp = client.post(
        f"/api/v1/pathways/enrollments/{enrollment_id}/milestones/{ms_id}/complete",
        headers=headers,
        json={"milestone_id": ms_id, "notes": "Completed on arrival"},
    )
    assert ms_resp.status_code == 200

    # 4. Advance stage
    adv_resp = client.post(
        f"/api/v1/pathways/enrollments/{enrollment_id}/advance-stage",
        headers=headers,
        json={"variance_reason": None},
    )
    assert adv_resp.status_code == 200
    assert adv_resp.json()["current_stage_id"] == pathway.stages[1].stage_id

    # 5. Patient pathways query
    pat_resp = client.get(f"/api/v1/pathways/patient/{patient.patient_id}", headers=headers)
    assert pat_resp.status_code == 200
    assert len(pat_resp.json()) >= 1

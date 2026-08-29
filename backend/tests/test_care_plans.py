"""Comprehensive test suite for Clinical Workflow Orchestration, Care Plans & Tasks.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
Tests:
- Care plan creation and validation (goals, interventions, draft default)
- Care plan retrieval and listing
- Care plan updates and finalized plan protection
- Physician review, signoff, and activation
- Care task creation, assignment, and overdue detection
- Care task completion with outcome notes
- AI-assisted care plan draft synthesis (ensuring DRAFT status and is_ai_generated flag)
- Background task worker integration
- FHIR R4 CarePlan and Task serialization
- Strict RBAC and cross-patient isolation
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.ai.task_worker import get_background_task_provider, reset_background_task_provider
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.care_plan import CarePlanCategory, CarePlanStatus
from app.schemas.care_task import CareTaskStatus, CareTaskType, TaskPriority


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "care_doc@hospital.org",
    name: str = "Dr. Care Orchestrator",
) -> tuple[dict[str, str], int]:
    """Register and login helper returning authorization headers and user ID."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "role": role.value,
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_create_and_retrieve_care_plan(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify care plan creation with structured goals and interventions."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_plan_create@test.com")

    res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-plans",
        headers=headers,
        json={
            "title": "Hypertension & Cardiovascular Health Plan",
            "category": "chronic_disease_management",
            "description": "Multi-month regimen targeting blood pressure reduction and lifestyle modification.",
            "intent": "plan",
            "goals": [
                {
                    "goal_id": "G-01",
                    "title": "Achieve Resting BP < 130/80 mmHg",
                    "target_metric": "<130/80 mmHg",
                    "status": "in_progress",
                }
            ],
            "interventions": [
                {
                    "intervention_id": "INT-01",
                    "description": "Home blood pressure monitoring twice daily.",
                    "category": "monitoring",
                    "responsible_party": "patient",
                }
            ],
        },
    )
    assert res.status_code == 201
    plan_data = res.json()
    assert plan_data["title"] == "Hypertension & Cardiovascular Health Plan"
    assert plan_data["status"] == CarePlanStatus.DRAFT.value
    assert plan_data["plan_id"].startswith("CP-")
    assert len(plan_data["goals_json"]) == 1
    assert len(plan_data["interventions_json"]) == 1

    plan_id = plan_data["plan_id"]

    # Retrieve specific plan
    get_res = client.get(f"/api/v1/care-plans/{plan_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["plan_id"] == plan_id


def test_update_care_plan_and_finalize_protection(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify editing draft plans and ensuring completed plans cannot be modified."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_plan_update@test.com")

    # 1. Create Draft
    create_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-plans",
        headers=headers,
        json={
            "title": "Draft Care Plan",
            "category": "preventive_care",
            "description": "Initial draft description.",
        },
    )
    plan_id = create_res.json()["plan_id"]

    # 2. Update Draft Description
    update_res = client.patch(
        f"/api/v1/care-plans/{plan_id}",
        headers=headers,
        json={"description": "Updated refined description for wellness."},
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated refined description for wellness."

    # 3. Mark Complete
    complete_res = client.post(f"/api/v1/care-plans/{plan_id}/complete", headers=headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == CarePlanStatus.COMPLETED.value

    # 4. Attempt to modify completed plan (MUST FAIL)
    failed_mod = client.patch(
        f"/api/v1/care-plans/{plan_id}",
        headers=headers,
        json={"title": "Illegal Edit on Completed Plan"},
    )
    assert failed_mod.status_code == 400


def test_physician_review_and_activation_lifecycle(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify physician review, mandatory confirm_accuracy flag, and transition to active status."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_review_plan@test.com")

    create_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-plans",
        headers=headers,
        json={
            "title": "Post-Discharge Recovery Plan",
            "category": "post_discharge_followup",
            "description": "Post-admission transitional management.",
        },
    )
    plan_id = create_res.json()["plan_id"]
    assert create_res.json()["status"] == CarePlanStatus.DRAFT.value

    # 1. Attempt review without confirmation (MUST FAIL)
    fail_res = client.post(
        f"/api/v1/care-plans/{plan_id}/review",
        headers=headers,
        json={"confirm_accuracy": False},
    )
    assert fail_res.status_code == 400

    # 2. Review and Activate
    review_res = client.post(
        f"/api/v1/care-plans/{plan_id}/review",
        headers=headers,
        json={
            "confirm_accuracy": True,
            "clinician_notes": "Reviewed and approved for immediate activation.",
            "activate_immediately": True,
        },
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == CarePlanStatus.ACTIVE.value
    assert review_res.json()["reviewed_at"] is not None


def test_care_task_creation_overdue_detection_and_completion(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify care task creation, priority assignment, overdue detection, and completion."""
    headers, _ = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="staff_tasks@test.com")

    # 1. Create Overdue Task (due yesterday)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    res1 = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-tasks",
        headers=headers,
        json={
            "title": "Urgent Stat Electrolyte Panel",
            "task_type": "lab_test_order",
            "priority": "STAT",
            "due_date": yesterday,
            "instructions": "Draw stat venous blood sample for K+ check.",
        },
    )
    assert res1.status_code == 201
    task1 = res1.json()
    assert task1["priority"] == TaskPriority.STAT.value
    assert task1["is_overdue"] is True
    task_id = task1["task_id"]

    # 2. Complete Task
    comp_res = client.post(
        f"/api/v1/care-tasks/{task_id}/complete",
        headers=headers,
        json={"completion_notes": "Sample drawn and sent to lab stat. Results pending in EHR."},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == CareTaskStatus.COMPLETED.value
    assert comp_res.json()["is_overdue"] is False
    assert "Sample drawn and sent" in comp_res.json()["completion_notes"]


from unittest.mock import patch
from tests.conftest import TestingSessionLocal


def test_ai_care_plan_synthesis_and_worker(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify AI Care Plan synthesis creates DRAFT plans with is_ai_generated=True and enqueued worker tasks."""
    reset_background_task_provider()
    get_background_task_provider(provider_type="sync", force_new=False)

    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_ai_synth@test.com")

    with patch("app.services.care_plan_service.SessionLocal", TestingSessionLocal):
        # Enqueue AI Synthesis
        synth_res = client.post(
            f"/api/v1/tasks/care-plans/synthesize?patient_id={test_patient.patient_id}",
            headers=headers,
            json={
                "category": "chronic_disease_management",
                "custom_instructions": "Focus on sodium restriction and weekly telemetry check.",
            },
        )
        assert synth_res.status_code == 202
        task_data = synth_res.json()
        assert task_data["task_type"] == "care_plan_generation"
        provider = get_background_task_provider()
        completed_task = provider.get_task(task_data["task_id"])
        assert completed_task is not None
        assert completed_task.error_message is None, f"Task failed with error: {completed_task.error_message}"

        # Verify synthesized plan was persisted in DRAFT status
        plans_res = client.get(f"/api/v1/patients/{test_patient.patient_id}/care-plans", headers=headers)
        assert plans_res.status_code == 200
        plans = plans_res.json()["items"]
        assert len(plans) >= 1

        ai_plan = next((p for p in plans if p["is_ai_generated"]), None)
        assert ai_plan is not None
        assert ai_plan["status"] == CarePlanStatus.DRAFT.value
        assert "Chronic Disease Management" in ai_plan["title"]
        assert len(ai_plan["goals_json"]) > 0



def test_fhir_r4_care_plan_and_task_export(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify exporting internal CarePlan and CareTask as FHIR R4 resources."""
    headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_fhir_care@test.com")


    # 1. Create Care Plan
    plan_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-plans",
        headers=headers,
        json={
            "title": "FHIR Interoperability Care Plan",
            "category": "rehabilitation",
            "description": "Physical therapy and cardiac rehabilitation plan.",
            "goals": [
                {
                    "goal_id": "G-REHAB-01",
                    "title": "Achieve 30-min walking endurance",
                    "status": "in_progress",
                }
            ],
            "interventions": [
                {
                    "intervention_id": "INT-PT-01",
                    "description": "Supervised treadmill exercise 3x weekly.",
                    "category": "rehabilitation",
                }
            ],
        },
    )
    plan_id = plan_res.json()["plan_id"]

    # 2. Create Care Task
    task_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-tasks",
        headers=headers,
        json={
            "title": "Physical Therapy Evaluation",
            "task_type": "general_task",
            "priority": "ROUTINE",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    task_id = task_res.json()["task_id"]

    # 3. Export FHIR CarePlan
    fhir_plan = client.get(f"/api/v1/fhir/CarePlan/{plan_id}", headers=headers)
    assert fhir_plan.status_code == 200
    assert fhir_plan.json()["resourceType"] == "CarePlan"
    assert fhir_plan.json()["id"] == plan_id
    assert fhir_plan.json()["subject"]["reference"] == f"Patient/{test_patient.patient_id}"

    # 4. Export FHIR Task
    fhir_task = client.get(f"/api/v1/fhir/Task/{task_id}", headers=headers)
    assert fhir_task.status_code == 200
    assert fhir_task.json()["resourceType"] == "Task"
    assert fhir_task.json()["id"] == task_id


def test_patient_role_rbac_restrictions(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify RBAC restrictions for Patient role."""
    headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="patient_unauth_care@test.com")

    # Patient cannot create care plans
    res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-plans",
        headers=headers,
        json={"title": "Unauthorized Plan", "description": "Test"},
    )
    assert res.status_code == 403

    # Patient cannot create tasks
    task_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/care-tasks",
        headers=headers,
        json={"title": "Unauthorized Task", "due_date": datetime.now(timezone.utc).isoformat()},
    )
    assert task_res.status_code == 403

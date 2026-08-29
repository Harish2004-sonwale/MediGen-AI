"""Unit and integration tests for Phase 9.0.11: Clinical Cohorts & Risk Stratification.

Validates:
- Cohort and disease registry CRUD and filtering
- Dynamic criteria evaluation and membership synchronization
- Multi-factorial clinical risk stratification scoring across risk types
- Cohort population health analytics and risk tier distributions
- Background task worker execution for cohort sync and risk calculation
- FHIR R4 Group and RiskAssessment serialization and export
- Strict RBAC and cross-patient data isolation
"""

from datetime import date, datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.cohort import CohortMembership, PatientCohort
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "cohort_doc@hospital.org",
    name: str = "Dr. Cohort Lead",
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


@pytest.fixture
def clinical_patient_record(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-COHORT-001",
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=date(1950, 4, 12),  # Senior (76 yrs)
        gender=Gender.FEMALE,
        email="eleanor.vance@example.com",
        phone="+1555019283",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Attach encounter with chronic condition keywords
    encounter = Encounter(
        encounter_id="ENC-COHORT-001",
        patient_id=patient.id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint="Severe dyspnea and lower extremity edema",
        assessment="Congestive Heart Failure, Stage 2 Hypertension, Type 2 Diabetes Mellitus",
        plan="Initiate daily diuretics and strict blood pressure monitoring",
        status=EncounterStatus.COMPLETED,
    )
    db_session.add(encounter)
    db_session.commit()
    return patient


@pytest.fixture
def secondary_patient_record(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-COHORT-002",
        first_name="Marcus",
        last_name="Brody",
        date_of_birth=date(1995, 8, 20),  # Young adult (31 yrs)
        gender=Gender.MALE,
        email="marcus.brody@example.com",
        phone="+1555019284",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    encounter = Encounter(
        encounter_id="ENC-COHORT-002",
        patient_id=patient.id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint="Mild seasonal sneezing",
        assessment="Allergic Rhinitis",
        plan="Over-the-counter antihistamines as needed",
        status=EncounterStatus.COMPLETED,
    )
    db_session.add(encounter)
    db_session.commit()
    return patient


def test_cohort_crud_lifecycle(
    client: TestClient,
    db_session: Session,
):
    """Test creating, retrieving, updating, and listing cohorts."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_crud@hospital.org")

    payload = {
        "name": "High-Risk Heart Failure Cohort",
        "description": "Longitudinal registry tracking geriatric patients with congestive heart failure.",
        "cohort_type": "disease_registry",
        "criteria": {
            "min_age": 65,
            "conditions": ["Heart Failure"],
        },
        "is_dynamic": True,
    }

    # 1. Create
    resp = client.post("/api/v1/cohorts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    cohort_id = data["cohort_id"]
    assert data["name"] == "High-Risk Heart Failure Cohort"
    assert data["is_dynamic"] is True
    assert data["criteria_json"]["min_age"] == 65

    # 2. Retrieve
    resp = client.get(f"/api/v1/cohorts/{cohort_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["cohort_id"] == cohort_id

    # 3. Update
    update_payload = {
        "name": "Updated Heart Failure & Cardiomyopathy Registry",
        "description": "Expanded registry with updated criteria.",
    }
    resp = client.patch(f"/api/v1/cohorts/{cohort_id}", json=update_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Heart Failure & Cardiomyopathy Registry"

    # 4. List
    resp = client.get("/api/v1/cohorts", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert any(c["cohort_id"] == cohort_id for c in resp.json()["items"])


def test_manual_and_dynamic_cohort_membership(
    client: TestClient,
    clinical_patient_record: Patient,
    secondary_patient_record: Patient,
    db_session: Session,
):
    """Test manual enrollment and dynamic criteria evaluation matching patients."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_membership@hospital.org")

    # Create dynamic cohort requiring Heart Failure and min age 60
    create_resp = client.post(
        "/api/v1/cohorts",
        json={
            "name": "Geriatric Cardiac Registry",
            "description": "Seniors with cardiac disease burden.",
            "cohort_type": "disease_registry",
            "criteria": {
                "min_age": 60,
                "conditions": ["Heart Failure"],
            },
            "is_dynamic": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    cohort_id = create_resp.json()["cohort_id"]

    # Eleanor (76 yrs, Heart Failure) should be auto-enrolled
    members_resp = client.get(f"/api/v1/cohorts/{cohort_id}/members", headers=headers)
    assert members_resp.status_code == 200
    members = members_resp.json()
    patient_ids = [m["patient_identifier"] for m in members]
    assert clinical_patient_record.patient_id in patient_ids
    # Marcus (31 yrs, Allergies) should NOT match
    assert secondary_patient_record.patient_id not in patient_ids

    # Manually add Marcus
    add_resp = client.post(
        f"/api/v1/cohorts/{cohort_id}/members",
        json={
            "patient_id": secondary_patient_record.patient_id,
            "notes": "Special clinical study inclusion",
        },
        headers=headers,
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["patient_identifier"] == secondary_patient_record.patient_id

    # Remove Marcus
    del_resp = client.delete(
        f"/api/v1/cohorts/{cohort_id}/members/{secondary_patient_record.patient_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200


def test_clinical_risk_stratification_scoring(
    client: TestClient,
    clinical_patient_record: Patient,
    db_session: Session,
):
    """Test multi-factorial clinical risk scoring evaluating age, comorbidities, vitals, and alerts."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_risk_score@hospital.org")

    # Add abnormal vitals to increase risk
    now = datetime.now(timezone.utc)
    vital = VitalTelemetry(
        reading_id="VIT-RISK-001",
        patient_id=clinical_patient_record.id,
        heart_rate=118,  # Tachycardia
        systolic_bp=168,  # Stage 2 Hypertension
        diastolic_bp=98,
        spo2_percent=89.5,  # Hypoxemia
        source="bedside_monitor",
        measured_at=now,
    )
    db_session.add(vital)

    # Add active critical CDS alert
    alert = ClinicalAlert(
        alert_id="ALT-RISK-001",
        patient_id=clinical_patient_record.id,
        alert_type="vital_sign_critical",
        severity="CRITICAL",
        status="active",
        title="Critical Hypoxemia Detected",
        explanation="SpO2 fallen below 90%.",
        last_triggered_at=now,
    )
    db_session.add(alert)
    db_session.commit()

    # Calculate 30-day Readmission Risk
    resp = client.post(
        f"/api/v1/patients/{clinical_patient_record.patient_id}/risk-assessments",
        json={
            "risk_type": "readmission_30d",
            "custom_context": "Post-emergency department evaluation.",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["patient_id"] == clinical_patient_record.id
    assert data["risk_type"] == "readmission_30d"
    assert data["risk_score"] >= 50.0  # High or critical due to age, heart failure, hypoxemia, alert
    assert data["risk_tier"] in ("HIGH", "CRITICAL")
    assert len(data["contributing_factors_json"]) >= 3
    assert len(data["mitigation_recommendations_json"]) >= 1

    assessment_id = data["assessment_id"]

    # Retrieve specific risk assessment
    get_resp = client.get(f"/api/v1/risk-assessments/{assessment_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["assessment_id"] == assessment_id

    # List patient risk assessments
    list_resp = client.get(
        f"/api/v1/patients/{clinical_patient_record.patient_id}/risk-assessments",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1


def test_cohort_population_analytics(
    client: TestClient,
    clinical_patient_record: Patient,
    db_session: Session,
):
    """Test population health analytics aggregation across cohort members."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_analytics@hospital.org")

    # Create cohort
    create_resp = client.post(
        "/api/v1/cohorts",
        json={
            "name": "Population Analytics Test Cohort",
            "description": "Cohort for verifying metric aggregation.",
            "cohort_type": "quality_measure",
            "is_dynamic": False,
        },
        headers=headers,
    )
    cohort_id = create_resp.json()["cohort_id"]

    # Enroll patient
    client.post(
        f"/api/v1/cohorts/{cohort_id}/members",
        json={"patient_id": clinical_patient_record.patient_id},
        headers=headers,
    )

    # Compute risk assessment for patient
    client.post(
        f"/api/v1/patients/{clinical_patient_record.patient_id}/risk-assessments",
        json={"risk_type": "clinical_deterioration"},
        headers=headers,
    )

    # Get analytics
    resp = client.get(f"/api/v1/cohorts/{cohort_id}/analytics", headers=headers)
    assert resp.status_code == 200
    analytics = resp.json()
    assert analytics["cohort_id"] == cohort_id
    assert analytics["total_members"] == 1
    assert "risk_tier_distribution" in analytics
    assert analytics["mean_risk_score"] > 0.0


def test_async_cohort_and_risk_background_workers(
    client: TestClient,
    clinical_patient_record: Patient,
    db_session: Session,
):
    """Test background worker task submission and synchronous execution functions."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_async_worker@hospital.org")

    # Create cohort
    cohort = PatientCohort(
        cohort_id="COHORT-ASYNC-001",
        name="Async Sync Cohort",
        description="Testing background evaluation worker",
        cohort_type="disease_registry",
        criteria_json={"min_age": 70},
        is_dynamic=True,
    )
    db_session.add(cohort)
    db_session.commit()

    # Enqueue background task
    enqueue_resp = client.post(f"/api/v1/tasks/cohorts/{cohort.cohort_id}/evaluate", headers=headers)
    assert enqueue_resp.status_code == 202
    assert "TASK-" in enqueue_resp.json()["task_id"]

    # Enqueue patient risk background task
    risk_task_resp = client.post(
        f"/api/v1/tasks/patients/{clinical_patient_record.patient_id}/stratify-risk",
        json={"risk_type": "readmission_30d"},
        headers=headers,
    )
    assert risk_task_resp.status_code == 202

    # Directly execute worker jobs with patched SessionLocal
    with patch("app.services.cohort_service.SessionLocal", TestingSessionLocal):
        from app.services.cohort_service import (
            execute_cohort_evaluation_job,
            execute_patient_risk_stratification_job,
        )

        res_eval = execute_cohort_evaluation_job(cohort.cohort_id)
        assert res_eval["status"] == "completed"

        res_risk = execute_patient_risk_stratification_job(
            patient_id=clinical_patient_record.patient_id,
            risk_type="readmission_30d",
        )
        assert "assessment_id" in res_risk
        assert res_risk["risk_score"] > 0


def test_fhir_r4_group_and_risk_assessment_export(
    client: TestClient,
    clinical_patient_record: Patient,
    db_session: Session,
):
    """Test exporting cohort as FHIR Group and risk assessment as FHIR RiskAssessment."""
    headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_fhir_cohort@hospital.org")


    # Create cohort with member
    create_resp = client.post(
        "/api/v1/cohorts",
        json={
            "name": "FHIR Export Test Cohort",
            "description": "Testing FHIR R4 Group export",
            "cohort_type": "disease_registry",
            "is_dynamic": False,
        },
        headers=headers,
    )
    cohort_id = create_resp.json()["cohort_id"]
    client.post(
        f"/api/v1/cohorts/{cohort_id}/members",
        json={"patient_id": clinical_patient_record.patient_id},
        headers=headers,
    )

    # 1. Export FHIR Group
    group_resp = client.get(f"/api/v1/fhir/Group/{cohort_id}", headers=headers)
    assert group_resp.status_code == 200
    fhir_group = group_resp.json()
    assert fhir_group["resourceType"] == "Group"
    assert fhir_group["id"] == cohort_id
    assert fhir_group["name"] == "FHIR Export Test Cohort"
    assert len(fhir_group["member"]) == 1

    # 2. Export FHIR RiskAssessment
    assess_resp = client.post(
        f"/api/v1/patients/{clinical_patient_record.patient_id}/risk-assessments",
        json={"risk_type": "cardiovascular_decompensation"},
        headers=headers,
    )
    assessment_id = assess_resp.json()["assessment_id"]

    risk_resp = client.get(f"/api/v1/fhir/RiskAssessment/{assessment_id}", headers=headers)
    assert risk_resp.status_code == 200
    fhir_risk = risk_resp.json()
    assert fhir_risk["resourceType"] == "RiskAssessment"
    assert fhir_risk["id"] == assessment_id
    assert fhir_risk["subject"]["reference"] == f"Patient/{clinical_patient_record.patient_id}"
    assert len(fhir_risk["prediction"]) >= 1


def test_rbac_and_patient_isolation(
    client: TestClient,
    db_session: Session,
    clinical_patient_record: Patient,
    secondary_patient_record: Patient,
):
    """Test RBAC restrictions preventing patients from accessing cohort registries or cross-patient risk data."""
    eleanor_headers, _ = get_auth_headers(
        client,
        role=UserRole.PATIENT,
        email=clinical_patient_record.email,
        name="Eleanor Vance",
    )

    # Eleanor CANNOT access population cohorts
    resp = client.get("/api/v1/cohorts", headers=eleanor_headers)
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/cohorts",
        json={"name": "Illegal", "description": "Illegal"},
        headers=eleanor_headers,
    )
    assert resp.status_code == 403

    # Eleanor CANNOT calculate risk assessments directly
    resp = client.post(
        f"/api/v1/patients/{clinical_patient_record.patient_id}/risk-assessments",
        json={"risk_type": "readmission_30d"},
        headers=eleanor_headers,
    )
    assert resp.status_code == 403

    # Eleanor CANNOT access Marcus's risk assessments
    resp = client.get(
        f"/api/v1/patients/{secondary_patient_record.patient_id}/risk-assessments",
        headers=eleanor_headers,
    )
    assert resp.status_code == 403

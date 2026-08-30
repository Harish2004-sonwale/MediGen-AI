"""Integration tests for Remote Patient Monitoring (RPM), PROMs & Telehealth Protocols.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "rpm_doc@hospital.org",
    name: str = "Dr. RPM Physician",
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


def _create_patient(db: Session, identifier: str, email: str | None = None) -> Patient:
    """Create active patient in database."""
    p = Patient(
        patient_id=identifier,
        first_name="Arthur",
        last_name="Dent",
        date_of_birth=date(1975, 6, 15),
        gender=Gender.MALE,
        status=PatientStatus.ACTIVE,
        email=email or f"{identifier.lower()}@hospital.org",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class TestRPMAndTelehealth:
    """Comprehensive test suite for Phase 9.0.15."""

    def test_rpm_program_enrollment_and_device_registration(self, client: TestClient, db_session: Session):
        """Test enrolling patient in RPM program and registering monitoring device."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_rpm1@hospital.org")
        patient = _create_patient(db_session, "PAT-RPM-001")

        # 1. Enroll in RPM Program
        enroll_payload = {
            "patient_id": patient.patient_id,
            "condition_name": "Essential Hypertension",
            "program_name": "Longitudinal Cardiovascular RPM Protocol",
            "target_cadence_days": 1,
            "clinical_goals": ["Maintain BP < 130/80 mmHg", "Daily morning telemetry logging"],
        }
        resp = client.post(
            "/api/v1/rpm/programs/enroll",
            json=enroll_payload,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        program = resp.json()
        assert program["program_id"].startswith("RPM-PROG-")
        assert program["condition_name"] == "Essential Hypertension"
        assert program["status"] == "active"

        # List programs
        list_resp = client.get(
            f"/api/v1/rpm/programs?patient_id={patient.patient_id}",
            headers=headers,
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

        # 2. Register Device
        dev_payload = {
            "patient_id": patient.patient_id,
            "device_type": "blood_pressure_cuff",
            "manufacturer": "Omron Healthcare",
            "model_number": "BP7000-Evolving",
            "serial_number": f"OMR-BP-{datetime.now(timezone.utc).timestamp()}",
            "supported_measurements": ["systolic_bp", "diastolic_bp", "heart_rate"],
        }
        dev_resp = client.post(
            "/api/v1/rpm/devices",
            json=dev_payload,
            headers=headers,
        )
        assert dev_resp.status_code == 201, dev_resp.text
        device = dev_resp.json()
        assert device["device_id"].startswith("DEV-")
        assert device["device_type"] == "blood_pressure_cuff"

        # List devices
        dev_list = client.get(
            f"/api/v1/rpm/devices?patient_id={patient.patient_id}",
            headers=headers,
        )
        assert dev_list.status_code == 200
        assert dev_list.json()["total"] >= 1

    def test_rpm_observation_ingestion_normal_and_abnormal(self, client: TestClient, db_session: Session):
        """Test telemetry ingestion with deterministic normal and abnormal evaluations."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_rpm2@hospital.org")
        patient = _create_patient(db_session, "PAT-RPM-002")

        # 1. Normal Observation
        norm_obs = {
            "patient_id": patient.patient_id,
            "observation_type": "systolic_bp",
            "numeric_value": 122.0,
            "secondary_value": 78.0,
            "unit_of_measure": "mmHg",
            "source_type": "bluetooth_sync",
        }
        resp1 = client.post(
            "/api/v1/rpm/observations",
            json=norm_obs,
            headers=headers,
        )
        assert resp1.status_code == 201, resp1.text
        obs1 = resp1.json()
        assert obs1["classification"] == "normal"
        assert obs1["numeric_value"] == 122.0

        # 2. Abnormal Observation
        abn_obs = {
            "patient_id": patient.patient_id,
            "observation_type": "systolic_bp",
            "numeric_value": 155.0,
            "secondary_value": 96.0,
            "unit_of_measure": "mmHg",
            "source_type": "bluetooth_sync",
        }
        resp2 = client.post(
            "/api/v1/rpm/observations",
            json=abn_obs,
            headers=headers,
        )
        assert resp2.status_code == 201, resp2.text
        obs2 = resp2.json()
        assert obs2["classification"] == "abnormal"

        # 3. Telemetry summary
        sum_resp = client.get(
            f"/api/v1/rpm/patients/{patient.patient_id}/summary",
            headers=headers,
        )
        assert sum_resp.status_code == 200
        summary = sum_resp.json()
        assert summary["total_observations_count"] >= 2
        assert summary["average_systolic_bp"] is not None

    def test_rpm_critical_threshold_and_automated_escalation(self, client: TestClient, db_session: Session):
        """Test critical threshold breach auto-triggering escalation alerts and CareTasks."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_rpm3@hospital.org")
        patient = _create_patient(db_session, "PAT-RPM-003")

        # Ingest Hypertensive Crisis BP
        crit_obs = {
            "patient_id": patient.patient_id,
            "observation_type": "systolic_bp",
            "numeric_value": 195.0,
            "secondary_value": 125.0,
            "unit_of_measure": "mmHg",
            "source_type": "cellular_gateway",
        }
        resp = client.post(
            "/api/v1/rpm/observations",
            json=crit_obs,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        obs = resp.json()
        assert obs["classification"] == "critical"

        # Verify Escalation Alert created
        alerts_resp = client.get(
            f"/api/v1/rpm/alerts?patient_id={patient.patient_id}",
            headers=headers,
        )
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()
        assert alerts["total"] >= 1
        crit_alert = alerts["items"][0]
        assert crit_alert["severity"] == "CRITICAL"
        assert crit_alert["status"] == "open"
        assert crit_alert["linked_care_task_id"] is not None

        # Clinician acknowledges alert
        ack_resp = client.post(
            f"/api/v1/rpm/alerts/{crit_alert['alert_id']}/acknowledge",
            json={"notes": "Clinician contacted patient via telephone; instructed extra dose of antihypertensive."},
            headers=headers,
        )
        assert ack_resp.status_code == 200
        assert ack_resp.json()["status"] == "acknowledged"

        # Clinician resolves alert
        res_resp = client.post(
            f"/api/v1/rpm/alerts/{crit_alert['alert_id']}/resolve",
            json={
                "clinical_action_taken": "Repeat manual telemetry showed 138/86 mmHg. Escalation resolved successfully.",
                "create_care_task": True,
            },
            headers=headers,
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "resolved"

    def test_prom_questionnaires_submission_and_deterministic_scoring(
        self, client: TestClient, db_session: Session
    ):
        """Test listing PROM definitions, submitting responses, and scoring algorithms."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_prom1@hospital.org")
        patient = _create_patient(db_session, "PAT-PROM-001")

        # 1. List PROM definitions
        prom_defs = client.get(
            "/api/v1/rpm/proms/definitions",
            headers=headers,
        )
        assert prom_defs.status_code == 200
        defs = prom_defs.json()["items"]
        assert len(defs) >= 3
        phq9_def = next(d for d in defs if d["prom_id"] == "PROM-PHQ9")
        assert phq9_def["title"] == "Patient Health Questionnaire (PHQ-9)"

        # 2. Submit PHQ-9 Response (Moderate Depression: Score 12)
        submit_payload = {
            "prom_id": "PROM-PHQ9",
            "patient_id": patient.patient_id,
            "answers": {
                "1": 2,
                "2": 2,
                "3": 2,
                "4": 1,
                "5": 1,
                "6": 1,
                "7": 1,
                "8": 2,
                "9": 0,
            },
            "clinical_notes": "Routine outpatient follow-up screening.",
        }
        sub_resp = client.post(
            "/api/v1/rpm/proms/responses",
            json=submit_payload,
            headers=headers,
        )
        assert sub_resp.status_code == 201, sub_resp.text
        prom_res = sub_resp.json()
        assert prom_res["response_id"].startswith("PRES-")
        assert prom_res["calculated_score"] == 12.0
        assert "Moderate" in prom_res["severity_interpretation"]

        # 3. Submit Response with Suicidal Ideation flag (Q9 > 0)
        safety_payload = {
            "prom_id": "PROM-PHQ9",
            "patient_id": patient.patient_id,
            "answers": {
                "1": 3,
                "2": 3,
                "3": 3,
                "4": 3,
                "5": 2,
                "6": 2,
                "7": 2,
                "8": 2,
                "9": 2,  # Positive suicidal ideation flag
            },
        }
        saf_resp = client.post(
            "/api/v1/rpm/proms/responses",
            json=safety_payload,
            headers=headers,
        )
        assert saf_resp.status_code == 201
        assert saf_resp.json()["calculated_score"] == 22.0

        # List patient PROM responses
        hist_resp = client.get(
            f"/api/v1/rpm/proms/responses?patient_id={patient.patient_id}",
            headers=headers,
        )
        assert hist_resp.status_code == 200
        assert hist_resp.json()["total"] >= 2

    def test_telehealth_session_scheduling_and_lifecycle(self, client: TestClient, db_session: Session):
        """Test virtual care telehealth session scheduling, pre-visit briefing, and lifecycle."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_tele1@hospital.org")
        patient = _create_patient(db_session, "PAT-TELE-001")

        start_time = datetime.now(timezone.utc) + timedelta(days=2)

        # 1. Schedule Telehealth Session
        tele_payload = {
            "patient_id": patient.patient_id,
            "scheduled_start": start_time.isoformat(),
            "visit_reason": "Quarterly Remote Hypertension & PROM Review",
        }
        resp = client.post(
            "/api/v1/rpm/telehealth/sessions",
            json=tele_payload,
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        session = resp.json()
        assert session["session_id"].startswith("TELE-")
        assert session["status"] == "scheduled"
        assert session["pre_visit_rpm_summary_json"] is not None
        assert "key_discussion_points" in session["pre_visit_rpm_summary_json"]

        # 2. Transition to IN_PROGRESS
        patch1 = client.patch(
            f"/api/v1/rpm/telehealth/sessions/{session['session_id']}",
            json={"status": "in_progress", "session_notes": "Virtual consultation started. Video connection stable."},
            headers=headers,
        )
        assert patch1.status_code == 200
        assert patch1.json()["status"] == "in_progress"
        assert patch1.json()["actual_start"] is not None

        # 3. Transition to COMPLETED with follow-up task
        patch2 = client.patch(
            f"/api/v1/rpm/telehealth/sessions/{session['session_id']}",
            json={
                "status": "completed",
                "session_notes": "Reviewed daily BP log. Patient adhering to DASH diet. Refilled Amlodipine 5mg.",
                "followup_instructions": "Repeat serum creatinine and potassium in 4 weeks.",
                "create_followup_task": True,
            },
            headers=headers,
        )
        assert patch2.status_code == 200
        completed = patch2.json()
        assert completed["status"] == "completed"
        assert completed["actual_end"] is not None

    def test_rpm_and_prom_rbac_patient_isolation(self, client: TestClient, db_session: Session):
        """Test strict patient cross-isolation for observations, PROMs, and virtual visits."""
        p1 = _create_patient(db_session, "PAT-ISO-001", email="pat1@hospital.org")
        p2 = _create_patient(db_session, "PAT-ISO-002", email="pat2@hospital.org")

        p1_headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="pat1@hospital.org", name="Patient One")
        p2_headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="pat2@hospital.org", name="Patient Two")

        # Patient 1 ingests observation
        client.post(
            "/api/v1/rpm/observations",
            json={
                "patient_id": p1.patient_id,
                "observation_type": "heart_rate",
                "numeric_value": 72.0,
                "unit_of_measure": "bpm",
            },
            headers=p1_headers,
        )

        # Patient 1 views own observations -> succeeds
        p1_obs = client.get(
            f"/api/v1/rpm/observations?patient_id={p1.patient_id}",
            headers=p1_headers,
        )
        assert p1_obs.status_code == 200
        assert p1_obs.json()["total"] >= 1

        # Patient 2 tries to view Patient 1's observations -> gets only own (0)
        p2_obs = client.get(
            f"/api/v1/rpm/observations?patient_id={p1.patient_id}",
            headers=p2_headers,
        )
        assert p2_obs.status_code == 200
        assert p2_obs.json()["total"] == 0

        # Patient 2 tries to ingest observation for Patient 1 -> rejected with 403
        bad_ingest = client.post(
            "/api/v1/rpm/observations",
            json={
                "patient_id": p1.patient_id,
                "observation_type": "heart_rate",
                "numeric_value": 80.0,
                "unit_of_measure": "bpm",
            },
            headers=p2_headers,
        )
        assert bad_ingest.status_code == 403

    def test_fhir_r4_rpm_and_prom_export(self, client: TestClient, db_session: Session):
        """Test FHIR R4 exports for Device, Questionnaire, and QuestionnaireResponse."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_fhir_rpm@hospital.org")
        patient = _create_patient(db_session, "PAT-FHIR-RPM")

        # 1. Create Device
        dev_resp = client.post(
            "/api/v1/rpm/devices",
            json={
                "patient_id": patient.patient_id,
                "device_type": "glucometer",
                "manufacturer": "Accu-Chek",
                "model_number": "Guide-Me",
                "serial_number": f"AC-GLU-{datetime.now(timezone.utc).timestamp()}",
            },
            headers=headers,
        )
        device = dev_resp.json()

        # Export Device
        fhir_dev = client.get(
            f"/api/v1/fhir/Device/{device['device_id']}",
            headers=headers,
        )
        assert fhir_dev.status_code == 200
        assert fhir_dev.json()["resourceType"] == "Device"
        assert fhir_dev.json()["manufacturer"] == "Accu-Chek"

        # 2. Export Questionnaire (PHQ-9)
        fhir_q = client.get(
            "/api/v1/fhir/Questionnaire/PROM-PHQ9",
            headers=headers,
        )
        assert fhir_q.status_code == 200
        assert fhir_q.json()["resourceType"] == "Questionnaire"
        assert len(fhir_q.json()["item"]) == 9

        # 3. Submit PROM Response & Export
        prom_sub = client.post(
            "/api/v1/rpm/proms/responses",
            json={
                "prom_id": "PROM-PHQ9",
                "patient_id": patient.patient_id,
                "answers": {"1": 1, "2": 1, "3": 1, "4": 1, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0},
            },
            headers=headers,
        )
        prom_res = prom_sub.json()

        fhir_qr = client.get(
            f"/api/v1/fhir/QuestionnaireResponse/{prom_res['response_id']}",
            headers=headers,
        )
        assert fhir_qr.status_code == 200
        assert fhir_qr.json()["resourceType"] == "QuestionnaireResponse"
        assert len(fhir_qr.json()["item"]) >= 1

    def test_rpm_background_task_dispatch(self, client: TestClient, db_session: Session):
        """Test enqueuing asynchronous background RPM telemetry processing."""
        headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_task_rpm@hospital.org")
        patient = _create_patient(db_session, "PAT-TASK-RPM")
        resp = client.post(
            f"/api/v1/rpm/tasks/observations/process?patient_id={patient.patient_id}",
            headers=headers,
        )
        assert resp.status_code == 202
        task = resp.json()
        assert task["task_type"] == "rpm_observation_processing"
        assert task["status"] in ["queued", "running", "completed"]

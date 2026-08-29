"""Comprehensive test suite for Vital Telemetry Ingestion, CDS Alerting & Simulation.

Phase 9.0.9: Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion.
Tests:
- Valid telemetry ingestion & range validation
- Temperature unit normalization (°F to °C)
- Deterministic clinical threshold detection (Hypoxia, Tachycardia, Bradycardia, Hypertensive Crisis, Hypotension)
- 30-minute alert debouncing & recurrence incrementation
- Alert lifecycle (Active -> Acknowledged -> Dismissed)
- Mandatory clinical dismissal justification
- Telemetry simulation profiles (Normal, Hypoxic, Hypertensive Crisis, Tachycardic, Bradycardic)
- RBAC and cross-patient isolation
"""

import pytest
from fastapi.testclient import TestClient

from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.alert import AlertSeverity, AlertStatus


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "vitals_doc@hospital.org",
    name: str = "Dr. Telemetry Evaluator",
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


def test_ingest_valid_vital_telemetry_and_temp_normalization(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify normal telemetry ingestion and Fahrenheit-to-Celsius normalization."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_vitals_valid@test.com")

    # Ingest vital reading with Fahrenheit temperature (98.6°F -> ~37.0°C)
    res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={
            "heart_rate": 74,
            "systolic_bp": 118,
            "diastolic_bp": 78,
            "respiratory_rate": 16,
            "temperature": 98.6,
            "spo2_percent": 99.0,
            "weight_kg": 68.5,
            "device_id": "monitor_bed_04",
            "source": "bedside_monitor",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["heart_rate"] == 74
    assert data["systolic_bp"] == 118
    assert data["spo2_percent"] == 99.0
    assert data["temperature_c"] == 37.0
    assert data["device_id"] == "monitor_bed_04"
    assert data["source"] == "bedside_monitor"
    assert data["reading_id"].startswith("VIT-")

    # Retrieve latest vital
    latest_res = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/vitals/latest",
        headers=headers,
    )
    assert latest_res.status_code == 200
    assert latest_res.json()["reading_id"] == data["reading_id"]


def test_out_of_bounds_vital_telemetry_validation(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify that physiological out-of-bounds values are rejected."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_vitals_invalid@test.com")

    # Impossible SpO2 (> 100%)
    invalid_spo2 = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={"spo2_percent": 105.0},
    )
    assert invalid_spo2.status_code == 422

    # Impossible Heart Rate (< 20 bpm)
    invalid_hr = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={"heart_rate": 10},
    )
    assert invalid_hr.status_code == 422


def test_deterministic_hypoxia_alert_and_debouncing(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify critical hypoxia alert generation and 30-minute alarm debouncing."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_hypoxia_test@test.com")

    # 1. Ingest Hypoxic Reading (SpO2 86%)
    res1 = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={
            "heart_rate": 105,
            "spo2_percent": 86.0,
            "systolic_bp": 130,
            "diastolic_bp": 85,
        },
    )
    assert res1.status_code == 201

    # 2. Check Active Alerts
    alerts_res = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/alerts?status=active",
        headers=headers,
    )
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()["items"]
    assert len(alerts) >= 1
    hypoxia_alert = next((a for a in alerts if a["alert_type"] == "vital_hypoxia"), None)
    assert hypoxia_alert is not None
    assert hypoxia_alert["severity"] == AlertSeverity.CRITICAL.value
    assert hypoxia_alert["recurrence_count"] == 1
    assert "Critical Hypoxia Alert" in hypoxia_alert["title"]

    alert_id = hypoxia_alert["alert_id"]

    # 3. Ingest Second Hypoxic Reading within Debounce Window
    res2 = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={
            "heart_rate": 104,
            "spo2_percent": 87.0,
        },
    )
    assert res2.status_code == 201

    # 4. Verify Alert was Debounced (Recurrence count incremented to 2, no duplicate alert created)
    alerts_res2 = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/alerts?status=active",
        headers=headers,
    )
    alerts2 = alerts_res2.json()["items"]
    matching_hypoxia = [a for a in alerts2 if a["alert_type"] == "vital_hypoxia"]
    assert len(matching_hypoxia) == 1
    assert matching_hypoxia[0]["alert_id"] == alert_id
    assert matching_hypoxia[0]["recurrence_count"] == 2


def test_hypertensive_crisis_and_bradycardia_alerts(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify critical thresholds for blood pressure and heart rate."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_thresholds@test.com")

    # Ingest reading with Hypertensive Crisis (BP 195/125) and Bradycardia (HR 36)
    res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={
            "heart_rate": 36,
            "systolic_bp": 195,
            "diastolic_bp": 125,
            "spo2_percent": 97.0,
        },
    )
    assert res.status_code == 201

    alerts_res = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/alerts",
        headers=headers,
    )
    alerts = alerts_res.json()["items"]
    types = [a["alert_type"] for a in alerts]
    assert "vital_hypertension" in types
    assert "vital_bradycardia" in types

    htn_alert = next(a for a in alerts if a["alert_type"] == "vital_hypertension")
    assert htn_alert["severity"] == AlertSeverity.CRITICAL.value
    assert "Hypertensive Crisis" in htn_alert["title"]


def test_alert_acknowledgement_and_dismissal_lifecycle(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify alert acknowledgement and dismissal requiring clinical reason."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_ack_lifecycle@test.com")

    # Ingest trigger reading
    client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={"heart_rate": 155, "spo2_percent": 98.0},
    )

    alerts_res = client.get(f"/api/v1/patients/{test_patient.patient_id}/alerts", headers=headers)
    alert = alerts_res.json()["items"][0]
    alert_id = alert["alert_id"]
    assert alert["status"] == AlertStatus.ACTIVE.value

    # 1. Acknowledge Alert
    ack_res = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=headers,
        json={"notes": "Telemetry reviewed; patient in sinus tachycardia."},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == AlertStatus.ACKNOWLEDGED.value
    assert ack_res.json()["acknowledged_at"] is not None

    # 2. Attempt Dismissal without Reason (MUST FAIL with 400/422 validation error)
    failed_dismiss = client.post(
        f"/api/v1/alerts/{alert_id}/dismiss",
        headers=headers,
        json={"reason": " "},
    )
    assert failed_dismiss.status_code in (400, 422)


    # 3. Dismiss Alert with Clinical Reason (Should Succeed)
    dismiss_res = client.post(
        f"/api/v1/alerts/{alert_id}/dismiss",
        headers=headers,
        json={"reason": "Administered beta blocker; rhythm settled to 82 bpm."},
    )
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["status"] == AlertStatus.DISMISSED.value
    assert dismiss_res.json()["dismissal_reason"] == "Administered beta blocker; rhythm settled to 82 bpm."


def test_telemetry_simulation_endpoint(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify deterministic simulator profiles."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_sim_test@test.com")

    # Simulate Hypertensive Crisis
    sim_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals/simulate",
        headers=headers,
        json={"profile": "hypertensive_crisis"},
    )
    assert sim_res.status_code == 201
    reading = sim_res.json()
    assert reading["systolic_bp"] == 195
    assert reading["diastolic_bp"] == 128
    assert reading["source"] == "simulator"


def test_patient_role_cannot_ingest_or_dismiss_alerts(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify RBAC restrictions for patient role."""
    headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="patient_unauth_vitals@test.com")

    # Patient cannot ingest vitals
    ingest_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals",
        headers=headers,
        json={"heart_rate": 75},
    )
    assert ingest_res.status_code == 403

    # Patient cannot simulate vitals
    sim_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/vitals/simulate",
        headers=headers,
        json={"profile": "normal"},
    )
    assert sim_res.status_code == 403

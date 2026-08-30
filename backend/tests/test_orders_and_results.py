"""Unit and integration tests for Phase 9.0.13: CPOE Orders & Closed-Loop Diagnostic Results.

Validates:
- Structured clinical order placement (CPOE) and duplicate order safety checks
- AI order set bundle suggestions (Chest Pain/ACS, Sepsis, DKA protocols)
- Diagnostic result ingestion with automated panic/critical threshold evaluation
- Automatic generation of CRITICAL ClinicalAlerts upon panic value detection
- Clinician closed-loop review and signoff workflow
- Asynchronous background task dispatch and synchronous job execution
- FHIR R4 ServiceRequest and DiagnosticReport serialization
- Strict RBAC and cross-patient data isolation
"""

from datetime import date, datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.models.encounter import Encounter
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "order_doc@hospital.org",
    name: str = "Dr. Attending Physician",
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
def test_order_patient(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-ORD-001",
        first_name="Arthur",
        last_name="Pendleton",
        date_of_birth=date(1965, 5, 20),
        gender=Gender.MALE,
        email="arthur.pendleton@example.com",
        phone="+1555019999",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Inpatient encounter
    encounter = Encounter(
        encounter_id="ENC-ORD-001",
        patient_id=patient.id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.EMERGENCY,

        chief_complaint="Substernal chest pressure radiating to left arm",
        assessment="Suspected Acute Coronary Syndrome, Chronic Kidney Disease Stage 3",
        plan="STAT ECG, serial cardiac enzymes, hold nephrotoxic agents",
        status=EncounterStatus.IN_PROGRESS,
    )
    db_session.add(encounter)
    db_session.commit()
    return patient


@pytest.fixture
def secondary_order_patient(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-ORD-002",
        first_name="Gwen",
        last_name="Stacy",
        date_of_birth=date(1995, 8, 12),
        gender=Gender.FEMALE,
        email="gwen.stacy@example.com",
        phone="+1555019998",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def test_place_clinical_order_and_duplicate_safety_flag(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test placing clinical orders and detecting 24h duplicate order safety warnings."""
    headers, user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_cpoe1@hospital.org")

    # 1. Place initial order
    order_payload = {
        "order_category": "laboratory",
        "order_type": "complete_blood_count",
        "priority": "routine",
        "clinical_indication": "Baseline inpatient admission evaluation",
        "specimen_source": "Venous blood",
    }
    resp1 = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json=order_payload,
        headers=headers,
    )
    assert resp1.status_code == 201, resp1.text
    order1 = resp1.json()
    assert order1["status"] == "placed"
    assert order1["order_type"] == "complete_blood_count"
    assert len(order1["ai_safety_flags_json"]) == 0

    # 2. Place identical order within 24h -> Should trigger DUPLICATE_ORDER_ALERT
    resp2 = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json=order_payload,
        headers=headers,
    )
    assert resp2.status_code == 201
    order2 = resp2.json()
    assert any(f["code"] == "DUPLICATE_ORDER_ALERT" for f in order2["ai_safety_flags_json"])

    # 3. Retrieve specific order
    get_resp = client.get(f"/api/v1/orders/{order1['order_id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["order_id"] == order1["order_id"]

    # 4. List patient orders
    list_resp = client.get(f"/api/v1/patients/{test_order_patient.patient_id}/orders", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2


def test_suggest_order_bundle(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test AI order bundle recommendation for Chest Pain / ACS and Sepsis."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_bundle@hospital.org")

    # 1. Chest Pain / ACS Bundle
    resp_acs = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders/suggest-bundle",
        json={"clinical_protocol": "chest_pain_acs"},
        headers=headers,
    )
    assert resp_acs.status_code == 200
    acs_data = resp_acs.json()
    assert "Chest Pain" in acs_data["protocol_name"]
    order_types = [o["order_type"] for o in acs_data["suggested_orders"]]
    assert "troponin_i_high_sensitivity" in order_types
    assert any(o["priority"] == "stat" for o in acs_data["suggested_orders"])

    # 2. Sepsis Protocol
    resp_sep = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders/suggest-bundle",
        json={"clinical_protocol": "sepsis_bundle"},
        headers=headers,
    )
    assert resp_sep.status_code == 200
    sep_data = resp_sep.json()
    assert "Sepsis" in sep_data["protocol_name"]
    sep_types = [o["order_type"] for o in sep_data["suggested_orders"]]
    assert "serum_lactate" in sep_types
    assert "blood_cultures_x2" in sep_types


def test_diagnostic_result_ingestion_and_panic_critical_alert(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test result ingestion with panic critical evaluation and automated alert dispatch."""
    headers, user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_panic@hospital.org")

    # Place order for Serum Potassium
    order_resp = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json={
            "order_category": "laboratory",
            "order_type": "serum_potassium",
            "priority": "stat",
            "clinical_indication": "Serial electrolyte monitoring",
        },
        headers=headers,
    )
    order_id = order_resp.json()["order_id"]

    # Ingest panic critical lab: Potassium = 6.8 mEq/L (Critical threshold > 6.2)
    res_resp = client.post(
        f"/api/v1/orders/{order_id}/results",
        json={
            "test_name": "Serum Potassium",
            "test_code_loinc": "2823-3",
            "numeric_value": 6.8,
            "unit_of_measure": "mEq/L",
            "reference_range_low": 3.5,
            "reference_range_high": 5.0,
            "critical_threshold_low": 2.8,
            "critical_threshold_high": 6.2,
            "findings_summary": "Severe hyperkalemia detected on automated analyzer.",
        },
        headers=headers,
    )
    assert res_resp.status_code == 201, res_resp.text
    result = res_resp.json()
    result_id = result["result_id"]
    assert result["abnormal_flag"] == "panic_critical"
    assert result["status"] == "final"

    # Verify original order status transitioned to completed
    order_chk = client.get(f"/api/v1/orders/{order_id}", headers=headers).json()
    assert order_chk["status"] == "completed"
    assert order_chk["completed_at"] is not None

    # Verify a ClinicalAlert of type CRITICAL_LAB was triggered in the database
    alerts = db_session.query(ClinicalAlert).filter(ClinicalAlert.patient_id == test_order_patient.id).all()
    assert any(a.alert_type == "CRITICAL_LAB" and a.severity == "CRITICAL" for a in alerts)


def test_diagnostic_result_clinician_review_signoff(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test clinician review and closed-loop signoff of diagnostic results."""
    doc_headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_signoff_lab@hospital.org")

    # Place order
    order_resp = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json={
            "order_category": "laboratory",
            "order_type": "complete_blood_count",
            "clinical_indication": "Routine CBC screen",
        },
        headers=doc_headers,
    )
    order_id = order_resp.json()["order_id"]

    # Ingest normal result
    res_resp = client.post(
        f"/api/v1/orders/{order_id}/results",
        json={
            "test_name": "Hemoglobin",
            "numeric_value": 14.2,
            "unit_of_measure": "g/dL",
            "reference_range_low": 12.0,
            "reference_range_high": 16.0,
            "findings_summary": "Hemoglobin within normal limits.",
        },
        headers=doc_headers,
    )
    result_id = res_resp.json()["result_id"]
    assert res_resp.json()["abnormal_flag"] == "normal"
    assert res_resp.json()["reviewed_at"] is None

    # Clinician signs off
    review_resp = client.post(
        f"/api/v1/diagnostic-results/{result_id}/review",
        json={"review_notes": "Results reviewed and acknowledged. No acute hematologic compromise."},
        headers=doc_headers,
    )
    assert review_resp.status_code == 200
    signed_res = review_resp.json()
    assert signed_res["reviewed_by_user_id"] == doc_id
    assert signed_res["reviewed_at"] is not None
    assert "No acute hematologic compromise" in signed_res["findings_summary"]


def test_async_order_and_result_background_workers(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test background task queuing and execution for order verification and result ingestion."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_async_ord@hospital.org")

    with patch("app.services.order_service.SessionLocal", TestingSessionLocal):
        # Place order
        ord_resp = client.post(
            f"/api/v1/patients/{test_order_patient.patient_id}/orders",
            json={
                "order_category": "imaging",
                "order_type": "ct_abdomen_pelvis_with_contrast",
                "clinical_indication": "Abdominal pain evaluation",
            },
            headers=headers,
        )
        order_id = ord_resp.json()["order_id"]

        # Enqueue verification task
        v_task_resp = client.post(
            f"/api/v1/tasks/patients/{test_order_patient.patient_id}/orders/{order_id}/verify",
            headers=headers,
        )
        assert v_task_resp.status_code == 202
        assert "TASK-" in v_task_resp.json()["task_id"]

        # Enqueue result ingestion task
        r_task_resp = client.post(
            f"/api/v1/tasks/orders/{order_id}/results/ingest",
            json={
                "test_name": "CT Abdomen Pelvis Report",
                "findings_summary": "No acute appendicitis or bowel obstruction. Normal appearance of solid organs.",
            },
            headers=headers,
        )
        assert r_task_resp.status_code == 202

        from app.services.order_service import (
            execute_order_verification_job,
            execute_result_ingestion_job,
        )

        res_v = execute_order_verification_job(test_order_patient.patient_id, order_id)
        assert res_v["status"] == "completed"

        res_i = execute_result_ingestion_job(
            order_id=order_id,
            test_name="Serum Troponin",
            numeric_value=0.08,
            unit_of_measure="ng/mL",
            findings_summary="Troponin elevation noted.",
        )
        assert res_i["status"] == "completed"
        assert res_i["abnormal_flag"] == "panic_critical"



def test_fhir_r4_service_request_and_diagnostic_report_export(
    client: TestClient,
    test_order_patient: Patient,
    db_session: Session,
):
    """Test exporting clinical orders as FHIR ServiceRequest and results as DiagnosticReport."""
    headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_fhir_ord@hospital.org")

    # Place order
    o_resp = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json={
            "order_category": "laboratory",
            "order_type": "troponin_i_high_sensitivity",
            "priority": "stat",
            "clinical_indication": "Rule out acute coronary syndrome",
        },
        headers=headers,
    )
    order_id = o_resp.json()["order_id"]

    # Ingest result
    r_resp = client.post(
        f"/api/v1/orders/{order_id}/results",
        json={
            "test_name": "Troponin I High Sensitivity",
            "test_code_loinc": "49563-0",
            "numeric_value": 0.005,
            "unit_of_measure": "ng/mL",
            "reference_range_high": 0.014,
            "findings_summary": "Negative for acute myocardial injury.",
        },
        headers=headers,
    )
    result_id = r_resp.json()["result_id"]

    # 1. Export FHIR ServiceRequest
    sr_resp = client.get(f"/api/v1/fhir/ServiceRequest/{order_id}", headers=headers)
    assert sr_resp.status_code == 200
    fhir_sr = sr_resp.json()
    assert fhir_sr["resourceType"] == "ServiceRequest"
    assert fhir_sr["id"] == order_id
    assert fhir_sr["priority"] == "stat"

    # 2. Export FHIR DiagnosticReport
    dr_resp = client.get(f"/api/v1/fhir/DiagnosticReport/{result_id}", headers=headers)
    assert dr_resp.status_code == 200
    fhir_dr = dr_resp.json()
    assert fhir_dr["resourceType"] == "DiagnosticReport"
    assert fhir_dr["id"] == result_id
    assert fhir_dr["code"]["coding"][0]["code"] == "49563-0"


def test_rbac_and_patient_isolation(
    client: TestClient,
    test_order_patient: Patient,
    secondary_order_patient: Patient,
    db_session: Session,
):
    """Test RBAC preventing unauthorized patient order placement or cross-patient data access."""
    arthur_headers, _ = get_auth_headers(
        client,
        role=UserRole.PATIENT,
        email=test_order_patient.email,
        name="Arthur Pendleton",
    )

    # Arthur CANNOT place orders
    resp = client.post(
        f"/api/v1/patients/{test_order_patient.patient_id}/orders",
        json={"order_type": "cbc", "clinical_indication": "Unauthorized"},
        headers=arthur_headers,
    )
    assert resp.status_code == 403

    # Arthur CANNOT record results
    resp = client.post(
        "/api/v1/orders/ORD-NONEXISTENT/results",
        json={"test_name": "Unauthorized", "findings_summary": "Unauthorized"},
        headers=arthur_headers,
    )
    assert resp.status_code == 403

    # Arthur CANNOT view Gwen's orders
    resp = client.get(
        f"/api/v1/patients/{secondary_order_patient.patient_id}/orders",
        headers=arthur_headers,
    )
    assert resp.status_code == 403

"""Unit & Integration Tests for HL7 CDS Hooks Specification v2.0."""

from datetime import date
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.models.patient import Patient
from app.schemas.alert import AlertSeverity, AlertStatus
from app.schemas.patient import Gender, PatientStatus


def test_cds_services_discovery(client: TestClient):
    """Verifies standard CDS Hooks discovery catalogue at /cds-services."""
    resp = client.get("/cds-services")
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert len(data["services"]) == 4

    hooks = [s["hook"] for s in data["services"]]
    assert "patient-view" in hooks
    assert "order-select" in hooks
    assert "order-sign" in hooks
    assert "appointment-book" in hooks


def test_cds_hook_patient_view_with_alert(client: TestClient, db_session: Session):
    """Verifies patient-view hook returns critical/warning cards when patient has active vital alert."""
    # 1. Create Patient
    patient = Patient(
        patient_id="PAT-CDS-001",
        first_name="Alice",
        last_name="Smith",
        date_of_birth=date(1980, 5, 20),
        gender=Gender.FEMALE,
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # 2. Seed active alert
    alert = ClinicalAlert(
        alert_id="ALT-CDS-001",
        patient_id=patient.id,
        alert_type="HYPOXIA",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Critical Hypoxia Detected",
        explanation="Patient SpO2 dropped to 84% on room air. Initiate supplemental oxygen.",
    )
    db_session.add(alert)
    db_session.commit()

    resp = client.post(
        "/cds-services/patient-view",
        json={
            "hook": "patient-view",
            "hookInstance": "inst-001",
            "context": {
                "userId": "Practitioner/doc-01",
                "patientId": "PAT-CDS-001",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert len(data["cards"]) >= 1

    card = data["cards"][0]
    assert card["indicator"] == "critical"
    assert "Critical Hypoxia" in card["summary"] or "HYPOXIA" in card["summary"]
    assert "supplemental oxygen" in card["detail"].lower()
    assert len(card["links"]) >= 1
    assert card["links"][0]["type"] == "smart"


def test_cds_hook_order_select_drug_interaction(client: TestClient):
    """Verifies order-select hook detects drug interaction and returns warning CDS Card with action suggestion."""
    resp = client.post(
        "/cds-services/order-select",
        json={
            "hook": "order-select",
            "hookInstance": "inst-002",
            "context": {
                "userId": "Practitioner/doc-01",
                "patientId": "PAT-001",
                "selections": ["Aspirin 325mg"],
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert len(data["cards"]) >= 1

    card = data["cards"][0]
    assert card["indicator"] in ("warning", "critical")
    assert "Safety Alert" in card["summary"]
    assert len(card["suggestions"]) >= 1
    assert card["suggestions"][0]["actions"][0]["type"] == "delete"


def test_cds_hook_order_sign_and_appointment_book(client: TestClient):
    """Verifies order-sign and appointment-book hook handlers return info cards."""
    # 1. order-sign
    sign_resp = client.post(
        "/cds-services/order-sign",
        json={
            "hook": "order-sign",
            "hookInstance": "inst-003",
            "context": {
                "userId": "Practitioner/doc-01",
                "patientId": "PAT-001",
            },
        },
    )
    assert sign_resp.status_code == 200
    assert len(sign_resp.json()["cards"]) >= 1
    assert sign_resp.json()["cards"][0]["indicator"] == "info"

    # 2. appointment-book
    appt_resp = client.post(
        "/cds-services/appointment-book",
        json={
            "hook": "appointment-book",
            "hookInstance": "inst-004",
            "context": {
                "userId": "Practitioner/doc-01",
                "patientId": "PAT-001",
            },
        },
    )
    assert appt_resp.status_code == 200
    assert len(appt_resp.json()["cards"]) >= 1
    assert appt_resp.json()["cards"][0]["indicator"] == "info"

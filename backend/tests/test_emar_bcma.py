"""Unit and integration tests for Phase 9.0.28: Closed-Loop Medication Administration (eMAR) & Barcode Verification (BCMA)."""

from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.emar import (
    HighAlertMedicationCategory,
    MARStatus,
    MedicationAdministrationRecord,
    MedicationBarcodeDirectory,
)
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import Gender, PatientStatus
from app.schemas.user import UserRole


@pytest.fixture
def auth_nurse_headers(db_session: Session):
    nurse = db_session.query(User).filter(User.email == "nurse.emar@hospital.org").first()
    if not nurse:
        nurse = User(
            email="nurse.emar@hospital.org",
            name="Nurse Jackie Peyton, RN",
            password_hash="mocknursehash",
            role=UserRole.HEALTHCARE_STAFF,
            is_active=True,
            default_facility_id="FAC-METRO-MAIN",
        )
        db_session.add(nurse)
        db_session.commit()
        db_session.refresh(nurse)
    token = create_access_token(subject=str(nurse.id), role=nurse.role.value)
    return {"Authorization": f"Bearer {token}"}, nurse


@pytest.fixture
def auth_witness_nurse(db_session: Session):
    from app.core.security import hash_password
    witness = db_session.query(User).filter(User.email == "witness.nurse@hospital.org").first()
    if not witness:
        witness = User(
            email="witness.nurse@hospital.org",
            name="Nurse Zoey Barkow, RN",
            password_hash=hash_password("SecretWitnessPass123!"),
            role=UserRole.HEALTHCARE_STAFF,
            is_active=True,
            default_facility_id="FAC-METRO-MAIN",
        )
        db_session.add(witness)
        db_session.commit()
        db_session.refresh(witness)
    return witness


@pytest.fixture
def setup_emar_patient_and_barcodes(db_session: Session):
    # Patient
    patient = db_session.query(Patient).filter(Patient.patient_id == "PAT-EMAR-001").first()
    if not patient:
        patient = Patient(
            patient_id="PAT-EMAR-001",
            first_name="Arthur",
            last_name="Dent",
            date_of_birth=date(1982, 3, 11),
            gender=Gender.MALE,
            status=PatientStatus.ACTIVE,
            facility_id="FAC-METRO-MAIN",
        )
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)

    # Barcode entries
    b1 = db_session.query(MedicationBarcodeDirectory).filter(MedicationBarcodeDirectory.barcode == "NDC-00069-0266-01").first()
    if not b1:
        b1 = MedicationBarcodeDirectory(
            barcode="NDC-00069-0266-01",
            medication_name="Amlodipine Besylate 5mg",
            rxnorm_code="RXNORM-17767",
            ndc_code="00069-0266-01",
            standard_dose="5mg",
            dosage_form="tablet",
            route="oral",
            is_high_alert=False,
        )
        db_session.add(b1)

    b2 = db_session.query(MedicationBarcodeDirectory).filter(MedicationBarcodeDirectory.barcode == "NDC-00002-8215-01").first()
    if not b2:
        b2 = MedicationBarcodeDirectory(
            barcode="NDC-00002-8215-01",
            medication_name="Insulin Regular (Humulin R) 100 units/mL",
            rxnorm_code="RXNORM-5856",
            ndc_code="00002-8215-01",
            standard_dose="10 units",
            dosage_form="injection",
            route="subcutaneous",
            is_high_alert=True,
            high_alert_category=HighAlertMedicationCategory.INSULIN,
        )
        db_session.add(b2)

    db_session.commit()
    db_session.refresh(b1)
    db_session.refresh(b2)

    return patient, b1, b2


def test_schedule_medication_doses(client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session):
    headers, _ = auth_nurse_headers
    patient, _, _ = setup_emar_patient_and_barcodes

    now = datetime.now(timezone.utc)
    payload = {
        "patient_id": patient.patient_id,
        "medication_name": "Amlodipine Besylate 5mg",
        "medication_code": "RXNORM-17767",
        "prescribed_dose": "5mg",
        "prescribed_route": "oral",
        "frequency_code": "Q12H",
        "total_doses": 4,
        "start_time": now.isoformat(),
    }

    resp = client.post("/api/v1/emar/schedule", json=payload, headers=headers)
    assert resp.status_code == 201
    doses = resp.json()
    assert len(doses) == 4
    assert doses[0]["status"] == "scheduled"
    assert doses[0]["medication_name"] == "Amlodipine Besylate 5mg"
    assert doses[0]["is_high_alert"] is False

    # Verify list schedule
    list_resp = client.get(f"/api/v1/emar/schedule/{patient.patient_id}", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 4


def test_bcma_5_rights_verification_success(client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session):
    headers, _ = auth_nurse_headers
    patient, b1, _ = setup_emar_patient_and_barcodes

    # Schedule dose
    now = datetime.now(timezone.utc)
    mar = MedicationAdministrationRecord(
        mar_id="MAR-TEST-001",
        patient_id=patient.id,
        facility_id="FAC-METRO-MAIN",
        medication_name="Amlodipine Besylate 5mg",
        medication_code="RXNORM-17767",
        prescribed_dose="5mg",
        prescribed_route="oral",
        prescribed_frequency="daily",
        scheduled_time=now,
        status=MARStatus.SCHEDULED,
        is_high_alert=False,
    )
    db_session.add(mar)
    db_session.commit()

    verify_payload = {
        "mar_id": mar.mar_id,
        "patient_id": patient.patient_id,
        "scanned_patient_barcode": patient.patient_id,
        "scanned_med_barcode": b1.barcode,
        "intended_dose": "5mg",
        "intended_route": "oral",
    }

    resp = client.post("/api/v1/emar/verify-5-rights", json=verify_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["verification_status"] == "pass"
    assert data["overall_passed"] is True
    assert data["patient_verification"]["passed"] is True
    assert data["medication_verification"]["passed"] is True
    assert data["dose_verification"]["passed"] is True
    assert data["route_verification"]["passed"] is True
    assert data["time_verification"]["passed"] is True


def test_bcma_5_rights_mismatch_rejected(client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session):
    headers, _ = auth_nurse_headers
    patient, _, _ = setup_emar_patient_and_barcodes

    verify_payload = {
        "patient_id": patient.patient_id,
        "scanned_patient_barcode": "PAT-WRONG-999",  # Wrong wristband
        "scanned_med_barcode": "NDC-00069-0266-01",
    }

    resp = client.post("/api/v1/emar/verify-5-rights", json=verify_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["verification_status"] == "mismatch_rejected"
    assert data["overall_passed"] is False
    assert data["patient_verification"]["passed"] is False
    assert len(data["discrepancy_warnings"]) >= 1


def test_administer_medication_success(client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session):
    headers, nurse = auth_nurse_headers
    patient, _, _ = setup_emar_patient_and_barcodes

    now = datetime.now(timezone.utc)
    mar = MedicationAdministrationRecord(
        mar_id="MAR-TEST-002",
        patient_id=patient.id,
        facility_id="FAC-METRO-MAIN",
        medication_name="Amlodipine Besylate 5mg",
        medication_code="RXNORM-17767",
        prescribed_dose="5mg",
        prescribed_route="oral",
        scheduled_time=now,
        status=MARStatus.SCHEDULED,
        is_high_alert=False,
        requires_dual_witness=False,
    )
    db_session.add(mar)
    db_session.commit()

    admin_payload = {
        "administered_dose": "5mg",
        "administered_route": "oral",
        "site_of_administration": "Oral Swallowed with Water",
        "scanned_patient_barcode": patient.patient_id,
        "scanned_med_barcode": "NDC-00069-0266-01",
        "vital_signs_pre_admin": {"blood_pressure": "128/82 mmHg", "heart_rate": 74},
        "patient_response_notes": "Tolerated medication well with no acute distress.",
    }

    resp = client.post(f"/api/v1/emar/records/{mar.mar_id}/administer", json=admin_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "administered"
    assert data["administering_nurse_id"] == nurse.id
    assert data["verification_passed"] is True
    assert data["actual_admin_time"] is not None


def test_high_alert_dual_witness_enforcement_and_flow(
    client: TestClient,
    auth_nurse_headers,
    auth_witness_nurse,
    setup_emar_patient_and_barcodes,
    db_session: Session,
):
    headers, nurse = auth_nurse_headers
    witness = auth_witness_nurse
    patient, _, b2 = setup_emar_patient_and_barcodes

    now = datetime.now(timezone.utc)
    mar = MedicationAdministrationRecord(
        mar_id="MAR-TEST-INSULIN-01",
        patient_id=patient.id,
        facility_id="FAC-METRO-MAIN",
        medication_name="Insulin Regular (Humulin R) 100 units/mL",
        medication_code="RXNORM-5856",
        prescribed_dose="10 units",
        prescribed_route="subcutaneous",
        scheduled_time=now,
        status=MARStatus.SCHEDULED,
        is_high_alert=True,
        requires_dual_witness=True,
    )
    db_session.add(mar)
    db_session.commit()

    # Attempt administer without dual signoff -> must be rejected
    admin_payload = {
        "administered_dose": "10 units",
        "administered_route": "subcutaneous",
        "site_of_administration": "Abdomen Right Lower Quadrant",
    }
    fail_resp = client.post(f"/api/v1/emar/records/{mar.mar_id}/administer", json=admin_payload, headers=headers)
    assert fail_resp.status_code == 400
    assert "High-Alert medication requires independent dual clinician witness" in fail_resp.json()["detail"]

    # Execute Dual Witness Signoff
    witness_payload = {
        "witness_user_email": witness.email,
        "witness_password": "SecretWitnessPass123!",
        "witness_notes": "Independent dose check: 10 units Insulin Regular verified against sliding scale order.",
    }
    witness_resp = client.post(f"/api/v1/emar/records/{mar.mar_id}/dual-signoff", json=witness_payload, headers=headers)
    assert witness_resp.status_code == 200
    witness_data = witness_resp.json()
    assert witness_data["dual_witness_user_id"] == witness.id

    # Now administration should succeed
    success_resp = client.post(f"/api/v1/emar/records/{mar.mar_id}/administer", json=admin_payload, headers=headers)
    assert success_resp.status_code == 200
    assert success_resp.json()["status"] == "administered"


def test_hold_or_refuse_dose_with_clinical_justification(
    client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session
):
    headers, nurse = auth_nurse_headers
    patient, _, _ = setup_emar_patient_and_barcodes

    now = datetime.now(timezone.utc)
    mar = MedicationAdministrationRecord(
        mar_id="MAR-TEST-HELD-01",
        patient_id=patient.id,
        facility_id="FAC-METRO-MAIN",
        medication_name="Metoprolol Tartrate 25mg",
        medication_code="RXNORM-6918",
        prescribed_dose="25mg",
        prescribed_route="oral",
        scheduled_time=now,
        status=MARStatus.SCHEDULED,
        is_high_alert=False,
    )
    db_session.add(mar)
    db_session.commit()

    hold_payload = {
        "status": "held",
        "clinical_reason": "Held dose due to pre-administration heart rate 48 bpm and SBP 92 mmHg.",
        "patient_response_notes": "Physician Dr. House notified regarding symptomatic bradycardia.",
    }

    resp = client.post(f"/api/v1/emar/records/{mar.mar_id}/hold-refuse", json=hold_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "held"
    assert "heart rate 48 bpm" in data["variance_reason"]


def test_barcode_directory_catalog(client: TestClient, auth_nurse_headers, setup_emar_patient_and_barcodes, db_session: Session):
    headers, _ = auth_nurse_headers

    resp = client.get("/api/v1/emar/barcodes?search=Insulin", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("Insulin" in item["medication_name"] for item in data["items"])

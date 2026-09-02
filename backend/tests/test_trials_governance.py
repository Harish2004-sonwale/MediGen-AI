"""Unit and integration tests for Phase 9.0.27: Multi-Center Clinical Trial Governance, Protocol Deviations & Regulatory Auditing."""

from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.patient import Patient
from app.models.trials import (
    BiomarkerObservation,
    ClinicalTrial,
    GenomicProfile,
    TrialEligibilityCriterion,
)
from app.models.trials_governance import (
    CAPARootCause,
    CAPAStatus,
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
    IRBSubmissionType,
    MultiCenterStudySite,
    StudySiteStatus,
    TrialCAPARecord,
    TrialIRBNotification,
    TrialProtocolDeviation,
)
from app.models.user import User


from app.schemas.user import UserRole


@pytest.fixture
def auth_headers(db_session: Session):
    user = db_session.query(User).filter(User.email == "dr.trials@hospital.org").first()
    if not user:
        user = User(
            email="dr.trials@hospital.org",
            name="Dr. Trial Coordinator",
            password_hash="mockhashedpassword",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_trial_and_patient(db_session: Session):
    # Create test trial
    trial = ClinicalTrial(
        trial_id="TRI-2026-IMMUNO-001",
        nct_number="NCT06129910",
        title="Phase II Anti-PD1 Plus Targeted Kinase Inhibitor in Advanced Solid Tumors",
        official_title="A Multicenter Phase 2 Study of Pembrolizumab with Kinase Inhibitors",
        sponsor="Global Oncology Research Group",
        phase="phase_2",
        status="recruiting",
        disease_condition="Metastatic Melanoma / NSCLC",
        intervention_name="Pembrolizumab + Trametinib",
        min_age_years=18,
        max_age_years=80,
        target_gender="all",
    )
    db_session.add(trial)
    db_session.flush()

    c1 = TrialEligibilityCriterion(
        criterion_id="CRIT-BRAF-01",
        trial_id=trial.id,
        category="genomics",
        criterion_type="inclusion",
        field_name="BRAF",
        expected_value_str="V600E",
        description="Documented BRAF V600E mutation",
        is_required=True,
    )
    c2 = TrialEligibilityCriterion(
        criterion_id="CRIT-AGE-18",
        trial_id=trial.id,
        category="demographics",
        criterion_type="inclusion",
        field_name="age",
        operator=">=",
        expected_value_num=18.0,
        description="Age greater than or equal to 18",
        is_required=True,
    )
    c3 = TrialEligibilityCriterion(
        criterion_id="CRIT-CNS-METS",
        trial_id=trial.id,
        category="clinical_history",
        criterion_type="exclusion",
        field_name="untreated_cns_metastases",
        expected_value_str="Active CNS metastases",
        description="Active untreated leptomeningeal disease or CNS metastasis",
        is_required=True,
    )
    db_session.add_all([c1, c2, c3])

    from app.schemas.patient import Gender, PatientStatus

    # Create patient
    patient = Patient(
        patient_id="PAT-TRI-001",
        first_name="Victor",
        last_name="Stone",
        date_of_birth=date(1985, 4, 12),
        gender=Gender.MALE,
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.flush()

    # Create genomic profile
    prof = GenomicProfile(
        profile_id="GEN-PROF-TEST01",
        patient_id=patient.id,
        test_name="Next-Gen Sequencing Solid Tumor Panel",
        specimen_type="Tumor Biopsy",
        sequencing_platform="Illumina NovaSeq 6000",
        overall_interpretation="Detected BRAF V600E activating mutation.",
    )
    db_session.add(prof)
    db_session.flush()

    # Create biomarker observation
    bio = BiomarkerObservation(
        observation_id="BIO-OBS-BRAF-01",
        profile_id=prof.id,
        patient_id=patient.id,
        gene_symbol="BRAF",
        variant_name="V600E",
        clinical_significance="Pathogenic / Responsive to Kinase Inhibitors",
    )
    db_session.add(bio)
    db_session.commit()
    db_session.refresh(trial)
    db_session.refresh(patient)

    return trial, patient


def test_create_and_list_study_sites(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, _ = setup_trial_and_patient

    create_payload = {
        "trial_id": trial.id,
        "site_name": "St. Jude Clinical Research Pavilion",
        "target_accrual": 40,
        "irb_approval_number": "IRB-SJ-2026-101",
        "irb_approval_date": "2026-03-01",
        "irb_expiry_date": "2027-02-28",
    }

    resp = client.post("/api/v1/trials-governance/sites", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["site_name"] == "St. Jude Clinical Research Pavilion"
    assert data["target_accrual"] == 40
    assert data["site_id"].startswith("SITE-")

    # List sites
    list_resp = client.get(f"/api/v1/trials-governance/sites?trial_id={trial.id}", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(s["site_name"] == "St. Jude Clinical Research Pavilion" for s in list_data["sites"])


def test_patient_prescreening_evaluation(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, patient = setup_trial_and_patient

    resp = client.get(f"/api/v1/trials-governance/prescreen/{patient.patient_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["patient_id"] == patient.patient_id
    assert data["total_trials_screened"] >= 1
    eval_match = next((e for e in data["evaluations"] if e["trial_id"] == trial.id), None)
    assert eval_match is not None
    assert eval_match["is_eligible"] is True
    assert eval_match["eligibility_score"] == 100.0
    assert len(eval_match["disqualifying_reasons"]) == 0


def test_report_protocol_deviation(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, patient = setup_trial_and_patient

    now_iso = datetime.now(timezone.utc).isoformat()
    dev_payload = {
        "trial_id": trial.id,
        "patient_id": patient.patient_id,
        "deviation_category": "investigational_product_dosing_error",
        "severity": "critical",
        "description": "Patient administered 200mg instead of protocol-mandated 100mg of investigational kinase inhibitor.",
        "occurred_at": now_iso,
        "discovered_at": now_iso,
        "impact_on_patient_safety": "Patient placed under 24-hour cardiac telemetry observation; vitals remained stable.",
        "impact_on_data_integrity": "Pharmacokinetic PK cycle 1 sample compromised.",
        "requires_irb_submission": True,
    }

    resp = client.post("/api/v1/trials-governance/deviations", json=dev_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["deviation_id"].startswith("DEV-")
    assert data["severity"] == "critical"
    assert data["status"] == "open"
    assert data["requires_irb_submission"] is True


def test_create_capa_and_status_transition(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, patient = setup_trial_and_patient
    user = db_session.query(User).filter(User.email == "dr.trials@hospital.org").first()

    now = datetime.now(timezone.utc)
    dev = TrialProtocolDeviation(
        deviation_id="DEV-2026-TEST01",
        trial_id=trial.id,
        patient_id=patient.id,
        reported_by_user_id=user.id,
        deviation_category=DeviationCategory.INFORMED_CONSENT_VARIANCE,
        severity=DeviationSeverity.MAJOR,
        status=DeviationStatus.OPEN,
        description="Consent form re-signature executed 2 days post-protocol amendment release.",
        occurred_at=now,
        discovered_at=now,
        requires_irb_submission=True,
    )
    db_session.add(dev)
    db_session.commit()
    db_session.refresh(dev)

    capa_payload = {
        "deviation_id": dev.id,
        "root_cause_category": "staff_training_gap",
        "root_cause_analysis": "Clinical research coordinator unfamiliar with electronic ICF re-consent automation.",
        "corrective_action": "Re-consent completed in presence of PI and signed electronically by subject.",
        "preventive_action": "Mandatory GCP refresher training assigned to all CRC staff on active trials.",
        "assigned_owner_user_id": user.id,
        "target_resolution_date": "2026-09-30",
    }

    resp = client.post(f"/api/v1/trials-governance/deviations/{dev.id}/capa", json=capa_payload, headers=auth_headers)
    assert resp.status_code == 201
    capa_data = resp.json()
    assert capa_data["capa_id"].startswith("CAPA-")
    assert capa_data["status"] == "in_progress"

    # Verify deviation updated to capa_assigned
    db_session.refresh(dev)
    assert dev.status == DeviationStatus.CAPA_ASSIGNED


def test_submit_irb_notification(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, patient = setup_trial_and_patient
    user = db_session.query(User).filter(User.email == "dr.trials@hospital.org").first()

    now = datetime.now(timezone.utc)
    dev = TrialProtocolDeviation(
        deviation_id="DEV-2026-TEST02",
        trial_id=trial.id,
        patient_id=patient.id,
        reported_by_user_id=user.id,
        deviation_category=DeviationCategory.SAFETY_REPORTING_DELAY,
        severity=DeviationSeverity.CRITICAL,
        status=DeviationStatus.OPEN,
        description="Grade 3 neutropenia event reported to sponsor 48 hours past the 24-hour IND reporting window.",
        occurred_at=now,
        discovered_at=now,
        requires_irb_submission=True,
    )
    db_session.add(dev)
    db_session.commit()
    db_session.refresh(dev)

    irb_payload = {
        "deviation_id": dev.id,
        "irb_committee_name": "Western Institutional Review Board (WIRB)",
        "submission_type": "prompt_safety_report_ind",
        "custom_remarks": "Safety oversight expedited filing per FDA 21 CFR Part 312.",
    }

    resp = client.post(f"/api/v1/trials-governance/deviations/{dev.id}/submit-irb", json=irb_payload, headers=auth_headers)
    assert resp.status_code == 200
    irb_data = resp.json()
    assert irb_data["notification_id"].startswith("IRB-NOTIF-")
    assert irb_data["acknowledgement_reference"] is not None
    assert irb_data["document_content_json"]["irb_committee"] == "Western Institutional Review Board (WIRB)"

    # Verify deviation status updated to irb_notified
    db_session.refresh(dev)
    assert dev.status == DeviationStatus.IRB_NOTIFIED


def test_trial_governance_summary(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, _ = setup_trial_and_patient

    site = MultiCenterStudySite(
        site_id="SITE-MH-TEST-01",
        trial_id=trial.id,
        facility_id="FAC-METRO-MAIN",
        site_name="MetroHealth Cancer Pavilion",
        target_accrual=50,
        current_enrolled=25,
        site_status=StudySiteStatus.ACTIVE,
    )
    db_session.add(site)
    db_session.commit()

    resp = client.get(f"/api/v1/trials-governance/trials/{trial.id}/summary", headers=auth_headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["trial_id"] == trial.id
    assert summary["total_target_accrual"] >= 50
    assert summary["total_enrolled"] >= 25
    assert len(summary["sites_metrics"]) >= 1


def test_unauthorized_deviation_reporting_rejected(client: TestClient, setup_trial_and_patient, db_session: Session):
    trial, patient = setup_trial_and_patient

    # Create patient user without doctor/staff role
    pat_user = User(
        email="patient.user@hospital.org",
        name="Patient User",
        password_hash="mockhash",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(pat_user)
    db_session.commit()
    db_session.refresh(pat_user)

    pat_token = create_access_token(subject=str(pat_user.id), role=pat_user.role.value)
    headers = {"Authorization": f"Bearer {pat_token}"}

    now_iso = datetime.now(timezone.utc).isoformat()
    dev_payload = {
        "trial_id": trial.id,
        "deviation_category": "missed_study_visit",
        "severity": "minor",
        "description": "Patient missed study visit due to transport issues.",
        "occurred_at": now_iso,
        "discovered_at": now_iso,
    }

    resp = client.post("/api/v1/trials-governance/deviations", json=dev_payload, headers=headers)
    assert resp.status_code in (401, 403)


def test_filter_deviations_by_severity(client: TestClient, auth_headers: dict, setup_trial_and_patient, db_session: Session):
    trial, _ = setup_trial_and_patient
    user = db_session.query(User).filter(User.email == "dr.trials@hospital.org").first()

    now = datetime.now(timezone.utc)
    d_crit = TrialProtocolDeviation(
        deviation_id="DEV-2026-CRIT01",
        trial_id=trial.id,
        reported_by_user_id=user.id,
        deviation_category=DeviationCategory.SAFETY_REPORTING_DELAY,
        severity=DeviationSeverity.CRITICAL,
        status=DeviationStatus.OPEN,
        description="Critical safety delay test",
        occurred_at=now,
        discovered_at=now,
    )
    d_minor = TrialProtocolDeviation(
        deviation_id="DEV-2026-MIN01",
        trial_id=trial.id,
        reported_by_user_id=user.id,
        deviation_category=DeviationCategory.LABORATORY_OUT_OF_WINDOW,
        severity=DeviationSeverity.MINOR,
        status=DeviationStatus.RESOLVED,
        description="Minor lab window variance test",
        occurred_at=now,
        discovered_at=now,
    )
    db_session.add_all([d_crit, d_minor])
    db_session.commit()

    resp = client.get(f"/api/v1/trials-governance/deviations?trial_id={trial.id}&severity=critical", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["severity"] == "critical" for d in data["deviations"])
    assert any(d["deviation_id"] == "DEV-2026-CRIT01" for d in data["deviations"])


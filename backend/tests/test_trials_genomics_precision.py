"""Integration tests for Clinical Trials Matching, Genomics & Precision Oncology.

Phase 9.0.16: Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility.
"""

from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.trials import BiomarkerObservation, ClinicalTrial, GenomicProfile, TrialMatch
from app.models.user import UserRole
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "oncologist@hospital.org",
    name: str = "Dr. Precision Oncologist",
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


def _create_patient(
    db: Session, identifier: str, dob: date = date(1968, 5, 20), email: str | None = None
) -> Patient:
    """Create active oncology patient in database."""
    p = Patient(
        patient_id=identifier,
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=dob,
        gender=Gender.FEMALE,
        status=PatientStatus.ACTIVE,
        email=email or f"{identifier.lower()}@hospital.org",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


class TestClinicalTrialsAndPrecisionOncology:
    """Comprehensive test suite for Phase 9.0.16."""

    def test_trial_crud_and_criteria_creation(self, client: TestClient):
        """Test creating, retrieving, listing, and adding structured eligibility criteria to a clinical trial."""
        doc_headers, _ = get_auth_headers(client, email="trial_admin@hospital.org", name="Dr. Trial Lead")

        # 1. Create Trial
        trial_payload = {
            "trial_id": "TRIAL-TEST-001",
            "nct_number": "NCT09912345",
            "title": "Phase 2 Study of KRAS G12C Inhibitor in Advanced NSCLC",
            "official_title": "Open-Label Phase 2 Investigation of Novel Small Molecule KRAS Inhibitor",
            "sponsor": "Precision Oncology Institute",
            "phase": "phase_2",
            "status": "recruiting",
            "disease_condition": "Non-Small Cell Lung Cancer",
            "intervention_name": "MG-KRAS-99",
            "intervention_type": "targeted_therapy",
            "min_age_years": 18,
            "max_age_years": 80,
            "target_gender": "all",
            "summary": "Investigational targeted therapy for KRAS G12C-mutated metastatic NSCLC.",
            "criteria": [
                {
                    "category": "diagnosis",
                    "criterion_type": "inclusion",
                    "field_name": "diagnosis",
                    "operator": "==",
                    "expected_value_str": "Non-Small Cell Lung Cancer",
                    "description": "Histologically confirmed metastatic Non-Small Cell Lung Cancer",
                    "is_required": True,
                },
                {
                    "category": "biomarker",
                    "criterion_type": "inclusion",
                    "field_name": "KRAS",
                    "operator": "PRESENT",
                    "expected_value_str": "KRAS",
                    "expected_value_json": "G12C",
                    "description": "Documented KRAS G12C mutation",
                    "is_required": True,
                },
            ],
        }

        create_res = client.post("/api/v1/trials", json=trial_payload, headers=doc_headers)
        assert create_res.status_code == 201, create_res.text
        data = create_res.json()
        assert data["trial_id"] == "TRIAL-TEST-001"
        assert data["sponsor"] == "Precision Oncology Institute"

        # 2. Add an Exclusion Criterion
        crit_payload = {
            "category": "biomarker",
            "criterion_type": "exclusion",
            "field_name": "EGFR",
            "operator": "ABSENT",
            "expected_value_str": "EGFR",
            "description": "Exclusion: Co-occurring activating EGFR mutations",
            "is_required": True,
        }
        crit_res = client.post("/api/v1/trials/TRIAL-TEST-001/criteria", json=crit_payload, headers=doc_headers)
        assert crit_res.status_code == 201
        crit_data = crit_res.json()
        assert crit_data["field_name"] == "EGFR"
        assert crit_data["criterion_type"] == "exclusion"

        # 3. Retrieve Trial Details
        get_res = client.get("/api/v1/trials/TRIAL-TEST-001", headers=doc_headers)
        assert get_res.status_code == 200
        detail = get_res.json()
        assert len(detail["criteria"]) == 3

        # 4. List Trials with Filter
        list_res = client.get("/api/v1/trials?phase=phase_2", headers=doc_headers)
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1

    def test_genomic_profile_and_biomarker_ingestion(self, client: TestClient):
        """Test uploading patient NGS genomic profile panels and adding structured biomarker findings."""
        doc_headers, _ = get_auth_headers(client, email="genomics_doc@hospital.org", name="Dr. Genomics")
        db: Session = TestingSessionLocal()
        patient = _create_patient(db, "PAT-GEN-001")

        # 1. Register Genomic Profile
        profile_payload = {
            "specimen_type": "tumor_tissue_biopsy",
            "specimen_collected_at": datetime.now(timezone.utc).isoformat(),
            "test_name": "Comprehensive NGS 500-Gene Solid Tumor Panel",
            "sequencing_platform": "Illumina NovaSeq 6000",
            "performing_lab": "MediGen Precision Genomics Core",
            "accession_number": "ACC-NGS-8891",
            "tumor_mutation_burden": 12.5,
            "microsatellite_instability_status": "MSI-H",
            "overall_interpretation": "High TMB and MSI-H with actionable EGFR L858R mutation detected.",
            "biomarkers": [
                {
                    "gene_symbol": "EGFR",
                    "variant_name": "L858R",
                    "alteration_type": "missense_mutation",
                    "hgvs_notation": "c.2573T>G (p.Leu858Arg)",
                    "chromosome": "7",
                    "genomic_position": "chr7:55259515",
                    "reference_allele": "T",
                    "alternate_allele": "G",
                    "zygosity": "heterozygous",
                    "variant_allele_fraction": 38.5,
                    "pathogenicity": "tier_1_strong_clinical",
                    "evidence_level": "FDA_Level_A",
                    "clinical_significance": "Actionable sensitivity to 3rd-gen EGFR TKIs (Osimertinib).",
                },
                {
                    "gene_symbol": "PD-L1",
                    "variant_name": "Expression",
                    "alteration_type": "expression_level",
                    "numeric_expression_value": 75.0,
                    "expression_unit": "%",
                    "pathogenicity": "tier_1_strong_clinical",
                    "evidence_level": "FDA_Level_A",
                    "clinical_significance": "High PD-L1 expression (TPS 75%) predicts strong response to Anti-PD-1 immunotherapy.",
                },
            ],
        }

        res = client.post(f"/api/v1/patients/{patient.patient_id}/genomic-profiles", json=profile_payload, headers=doc_headers)
        assert res.status_code == 201, res.text
        prof_data = res.json()
        assert prof_data["patient_id"] == patient.id
        assert prof_data["tumor_mutation_burden"] == 12.5

        # 2. Add an additional biomarker finding to the profile
        extra_bm = {
            "gene_symbol": "TP53",
            "variant_name": "R273H",
            "alteration_type": "missense_mutation",
            "pathogenicity": "pathogenic",
            "evidence_level": "Standard_Level_B",
            "clinical_significance": "Inactivating TP53 mutation associated with genomic instability.",
        }
        bm_res = client.post(f"/api/v1/genomic-profiles/{prof_data['profile_id']}/biomarkers", json=extra_bm, headers=doc_headers)
        assert bm_res.status_code == 201
        assert bm_res.json()["gene_symbol"] == "TP53"

        # 3. Retrieve single profile
        get_res = client.get(f"/api/v1/genomic-profiles/{prof_data['profile_id']}", headers=doc_headers)
        assert get_res.status_code == 200
        assert len(get_res.json()["biomarkers"]) == 3

    def test_deterministic_trial_matching_matched_and_ineligible(self, client: TestClient):
        """Test exact biomarker and clinical matching yielding MATCHED vs INELIGIBLE outcomes."""
        doc_headers, _ = get_auth_headers(client, email="matcher_doc@hospital.org", name="Dr. Matching")
        db: Session = TestingSessionLocal()
        patient = _create_patient(db, "PAT-MATCH-001", dob=date(1965, 4, 10))

        # Add confirmed diagnosis encounter
        enc = Encounter(
            encounter_id="ENC-MATCH-001",
            patient_id=patient.id,
            encounter_type=EncounterType.INITIAL_CONSULTATION,
            status=EncounterStatus.COMPLETED,
            chief_complaint="Metastatic Non-Small Cell Lung Cancer Stage IV consultation",
            assessment="Metastatic Non-Small Cell Lung Cancer Stage IV",
            clinical_notes="Genomic sequencing and targeted oncology review.",
        )
        db.add(enc)
        db.commit()


        # Add EGFR L858R biomarker profile
        prof = GenomicProfile(
            profile_id="GEN-PROF-MATCH-001",
            patient_id=patient.id,
            test_name="NGS Lung Oncology Panel",
        )
        db.add(prof)
        db.flush()
        bm = BiomarkerObservation(
            observation_id="BM-MATCH-001",
            profile_id=prof.id,
            patient_id=patient.id,
            gene_symbol="EGFR",
            variant_name="L858R",
            alteration_type="missense_mutation",
            pathogenicity="tier_1_strong_clinical",
        )
        db.add(bm)
        db.commit()

        # 1. Match against pre-seeded TRIAL-LUNG-001 (Requires NSCLC + EGFR L858R + Stage IV, excludes EGFR C797S)
        match_res = client.post(f"/api/v1/trials/TRIAL-LUNG-001/match/{patient.patient_id}", headers=doc_headers)
        assert match_res.status_code == 200, match_res.text
        m_data = match_res.json()
        assert m_data["match_status"] == "MATCHED"
        assert m_data["match_score"] == 100.0
        assert len(m_data["matched_criteria_json"]) >= 3
        assert len(m_data["failed_criteria_json"]) == 0
        assert "FULLY MATCHED" in m_data["overall_explanation"]
        assert len(m_data["provenance_hash"]) == 64

        # 2. Add an excluded resistance mutation (EGFR C797S) -> Should transition to INELIGIBLE
        bm_resis = BiomarkerObservation(
            observation_id="BM-RESIST-001",
            profile_id=prof.id,
            patient_id=patient.id,
            gene_symbol="EGFR",
            variant_name="C797S",
            alteration_type="missense_mutation",
            pathogenicity="pathogenic",
        )
        db.add(bm_resis)
        db.commit()

        rematch_res = client.post(f"/api/v1/trials/TRIAL-LUNG-001/match/{patient.patient_id}", headers=doc_headers)
        assert rematch_res.status_code == 200
        rematch_data = rematch_res.json()
        assert rematch_data["match_status"] == "INELIGIBLE"
        assert rematch_data["match_score"] == 0.0
        assert len(rematch_data["failed_criteria_json"]) >= 1
        assert "INELIGIBLE" in rematch_data["overall_explanation"]

    def test_missing_data_insufficient_and_potential_match(self, client: TestClient):
        """Test that missing clinical or genomic data produces POTENTIAL_MATCH / INSUFFICIENT_DATA and never assumes eligibility."""
        doc_headers, _ = get_auth_headers(client, email="triage_doc@hospital.org", name="Dr. Triage")
        db: Session = TestingSessionLocal()
        # Patient with no genomic profile and no encounters
        patient = _create_patient(db, "PAT-EMPTY-001")

        # 1. Match against TRIAL-BREAST-002 (Requires Breast Cancer + BRCA1)
        res = client.post(f"/api/v1/trials/TRIAL-BREAST-002/match/{patient.patient_id}", headers=doc_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["match_status"] in ("POTENTIAL_MATCH", "INSUFFICIENT_DATA")
        assert len(data["unknown_criteria_json"]) >= 1
        assert any(term in data["overall_explanation"] for term in ("INSUFFICIENT DATA", "POTENTIAL MATCH", "POTENTIAL_MATCH"))

    def test_numeric_biomarker_threshold_matching(self, client: TestClient):
        """Test numeric biomarker threshold evaluation (e.g. PD-L1 TPS >= 50%)."""
        doc_headers, _ = get_auth_headers(client, email="immuno_doc@hospital.org", name="Dr. Immuno")
        db: Session = TestingSessionLocal()
        patient = _create_patient(db, "PAT-PDL1-001")

        # Add diagnosis of Solid Tumors
        enc = Encounter(
            encounter_id="ENC-PDL1-001",
            patient_id=patient.id,
            encounter_type=EncounterType.INITIAL_CONSULTATION,
            status=EncounterStatus.COMPLETED,
            chief_complaint="Advanced Solid Malignancy staging",
            assessment="Advanced Solid Tumors",
            clinical_notes="Candidate for immune checkpoint inhibitor protocols.",
        )
        db.add(enc)
        db.commit()


        prof = GenomicProfile(
            profile_id="GEN-PROF-PDL1-001",
            patient_id=patient.id,
            test_name="IHC & Biomarker Panel",
        )
        db.add(prof)
        db.flush()

        # High PD-L1 expression: TPS 80%
        bm_high = BiomarkerObservation(
            observation_id="BM-PDL1-001",
            profile_id=prof.id,
            patient_id=patient.id,
            gene_symbol="PD-L1",
            variant_name="High Expression",
            alteration_type="expression_level",
            numeric_expression_value=80.0,
            expression_unit="%",
        )
        db.add(bm_high)
        db.commit()

        # Match against TRIAL-IMMUNO-003 (requires PD-L1 TPS >= 50%)
        res = client.post(f"/api/v1/trials/TRIAL-IMMUNO-003/match/{patient.patient_id}", headers=doc_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["match_status"] == "MATCHED"
        assert any(c["field_name"].lower() == "pd-l1" and c["status"] == "PASS" for c in data["matched_criteria_json"])

    def test_clinician_review_and_precision_treatment_eligibility(self, client: TestClient):
        """Test precision treatment decision-support synthesis and clinician review workflow."""
        doc_headers, _ = get_auth_headers(client, email="precision_onc@hospital.org", name="Dr. Precision Lead")
        db: Session = TestingSessionLocal()
        patient = _create_patient(db, "PAT-PREC-001")

        # Ingest EGFR L858R biomarker
        prof = GenomicProfile(
            profile_id="GEN-PROF-PREC-001",
            patient_id=patient.id,
            test_name="Targeted NGS Panel",
        )
        db.add(prof)
        db.flush()
        bm = BiomarkerObservation(
            observation_id="BM-PREC-001",
            profile_id=prof.id,
            patient_id=patient.id,
            gene_symbol="EGFR",
            variant_name="L858R",
            alteration_type="missense_mutation",
            pathogenicity="tier_1_strong_clinical",
        )
        db.add(bm)
        db.commit()

        # 1. Synthesize Precision Treatment Eligibility
        eval_res = client.post(f"/api/v1/patients/{patient.patient_id}/precision-eligibility/evaluate", headers=doc_headers)
        assert eval_res.status_code == 200, eval_res.text
        eval_data = eval_res.json()
        assert len(eval_data["items"]) >= 1
        rec = eval_data["items"][0]
        assert rec["gene_symbol"] == "EGFR"
        assert rec["variant_name"] == "L858R"
        assert "Osimertinib" in rec["recommended_intervention"]
        assert rec["eligibility_status"] == "ELIGIBLE"
        assert rec["clinician_review_status"] == "pending_review"

        # 2. Document Clinician Review
        review_payload = {
            "clinician_review_status": "approved_for_protocol",
            "review_notes": "Reviewed and confirmed Level 1A evidence. Proceed with Osimertinib 80mg Daily therapy protocol.",
        }
        rev_res = client.post(f"/api/v1/precision-eligibility/{rec['eligibility_id']}/review", json=review_payload, headers=doc_headers)
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert rev_data["clinician_review_status"] == "approved_for_protocol"
        assert rev_data["review_notes"] == review_payload["review_notes"]

    def test_rbac_patient_isolation_for_genomics_and_trials(self, client: TestClient):
        """Test strict patient data isolation for genomics, trial matches, and precision therapy."""
        doc_headers, _ = get_auth_headers(client, email="rbac_doc@hospital.org", name="Dr. RBAC")
        patient_a_headers, _ = get_auth_headers(
            client, role=UserRole.PATIENT, email="patient_a@hospital.org", name="Patient A"
        )
        patient_b_headers, _ = get_auth_headers(
            client, role=UserRole.PATIENT, email="patient_b@hospital.org", name="Patient B"
        )

        db: Session = TestingSessionLocal()
        pat_a = _create_patient(db, "PAT-ISO-A", email="patient_a@hospital.org")
        pat_b = _create_patient(db, "PAT-ISO-B", email="patient_b@hospital.org")

        # Doctor uploads genomic profile for Patient A
        prof_payload = {
            "specimen_type": "tumor_tissue_biopsy",
            "test_name": "Solid Tumor Panel",
        }
        client.post(f"/api/v1/patients/{pat_a.patient_id}/genomic-profiles", json=prof_payload, headers=doc_headers)

        # Patient A can access their own genomic profiles
        res_a = client.get(f"/api/v1/patients/{pat_a.patient_id}/genomic-profiles", headers=patient_a_headers)
        assert res_a.status_code == 200
        assert res_a.json()["total"] == 1

        # Patient B is forbidden from accessing Patient A's genomic profiles
        res_b = client.get(f"/api/v1/patients/{pat_a.patient_id}/genomic-profiles", headers=patient_b_headers)
        assert res_b.status_code == 403

        # Patient cannot register trials or trigger batch matches for others
        trial_create = client.post(
            "/api/v1/trials",
            json={"trial_id": "T-FAIL", "title": "Unauthorized", "sponsor": "X", "disease_condition": "Y", "intervention_name": "Z"},
            headers=patient_a_headers,
        )
        assert trial_create.status_code == 403

    def test_fhir_r4_trials_and_genomics_export_and_tasks(self, client: TestClient):
        """Test standard FHIR R4 exports (ResearchStudy, Observation, DiagnosticReport) and async background tasks."""
        doc_headers, _ = get_auth_headers(client, email="fhir_trials_doc@hospital.org", name="Dr. FHIR Trials")
        db: Session = TestingSessionLocal()
        patient = _create_patient(db, "PAT-FHIR-TR-001")

        # Ingest profile & biomarker
        prof = GenomicProfile(
            profile_id="GEN-PROF-FHIR-001",
            patient_id=patient.id,
            test_name="NGS Genomic Report",
        )
        db.add(prof)
        db.flush()
        bm = BiomarkerObservation(
            observation_id="BM-OBS-FHIR-001",
            profile_id=prof.id,
            patient_id=patient.id,
            gene_symbol="BRAF",
            variant_name="V600E",
            pathogenicity="tier_1_strong_clinical",
        )
        db.add(bm)
        db.commit()

        # 1. Export FHIR ResearchStudy
        rs_res = client.get("/api/v1/fhir/ResearchStudy/TRIAL-LUNG-001", headers=doc_headers)
        assert rs_res.status_code == 200, rs_res.text
        rs_data = rs_res.json()
        assert rs_data["resourceType"] == "ResearchStudy"
        assert rs_data["id"] == "TRIAL-LUNG-001"

        # 2. Export FHIR Observation (Biomarker)
        obs_res = client.get("/api/v1/fhir/Biomarker/BM-OBS-FHIR-001", headers=doc_headers)
        assert obs_res.status_code == 200, obs_res.text
        obs_data = obs_res.json()
        assert obs_data["resourceType"] == "Observation"
        assert obs_data["id"] == "BM-OBS-FHIR-001"
        assert obs_data["code"]["text"] == "BRAF V600E"

        # 3. Export FHIR DiagnosticReport (Genomic Profile)
        dr_res = client.get("/api/v1/fhir/GenomicProfile/GEN-PROF-FHIR-001", headers=doc_headers)
        assert dr_res.status_code == 200, dr_res.text
        dr_data = dr_res.json()
        assert dr_data["resourceType"] == "DiagnosticReport"
        assert dr_data["id"] == "GEN-PROF-FHIR-001"
        assert len(dr_data["result"]) >= 1

        # 4. Dispatch Async Background Task
        task_res = client.post(f"/api/v1/tasks/patients/{patient.patient_id}/trial-matching", headers=doc_headers)
        assert task_res.status_code == 202
        assert task_res.json()["task_type"] == "trial_matching"
        assert task_res.json()["status"] in ("queued", "completed", "running")

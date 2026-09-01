"""Unit and Integration Tests for Federated Enterprise Master Patient Index (EMPI)."""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient import Gender, PatientStatus
from app.schemas.user import UserRegisterRequest
from app.services.empi_service import (
    EMPIService,
    empi_service,
    jaro_winkler_similarity,
    levenshtein_similarity,
    soundex,
)
from app.services.user_service import create_user


@pytest.fixture
def empi_test_patients(db_session: Session):
    """Create a cohort of test patients with varying degrees of similarity."""
    p1 = Patient(
        patient_id="PAT-EMPI-001",
        first_name="Alexander",
        last_name="Hamilton",
        date_of_birth=date(1980, 1, 11),
        gender=Gender.MALE,
        email="alex.hamilton@example.com",
        phone="+1-555-0111",
        address="57 Wall St, New York, NY",
        emergency_contact_name="Eliza Hamilton",
        emergency_contact_phone="+1-555-0112",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-001",
    )
    # Exact duplicate at a different facility with slight typo in first name & address
    p2 = Patient(
        patient_id="PAT-EMPI-002",
        first_name="Alexandr",
        last_name="Hamilton",
        date_of_birth=date(1980, 1, 11),
        gender=Gender.MALE,
        email="alex.hamilton@example.com",
        phone="+1-555-0111",
        address="57 Wall Street, New York, NY",
        emergency_contact_name="Eliza Hamilton",
        emergency_contact_phone="+1-555-0112",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-002",
    )
    # Probable match with transposed birthday and nickname
    p3 = Patient(
        patient_id="PAT-EMPI-003",
        first_name="Alex",
        last_name="Hamiltone",
        date_of_birth=date(1980, 11, 1),
        gender=Gender.MALE,
        email="alexander.h@other.org",
        phone="+1-555-0111",
        address="57 Wall St, NY",
        emergency_contact_name="Elizabeth",
        emergency_contact_phone="+1-555-0112",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-003",
    )
    # Distinct patient
    p4 = Patient(
        patient_id="PAT-EMPI-004",
        first_name="Thomas",
        last_name="Jefferson",
        date_of_birth=date(1975, 4, 13),
        gender=Gender.MALE,
        email="thomas.j@monticello.org",
        phone="+1-555-0999",
        address="100 Albemarle Rd, Charlottesville, VA",
        emergency_contact_name="Martha",
        emergency_contact_phone="+1-555-0998",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-001",
    )
    db_session.add_all([p1, p2, p3, p4])
    db_session.commit()
    return [p1, p2, p3, p4]


def test_similarity_primitives():
    """Verify string distance and phonetic similarity algorithms."""
    # Jaro-Winkler
    assert jaro_winkler_similarity("Alexander", "Alexander") == 1.0
    assert jaro_winkler_similarity("Alexander", "Alexandr") > 0.90
    assert jaro_winkler_similarity("Hamilton", "Hamiltone") > 0.90
    assert jaro_winkler_similarity("Hamilton", "Jefferson") < 0.50

    # Levenshtein
    assert levenshtein_similarity("1234567890", "1234567890") == 1.0
    assert levenshtein_similarity("5550111", "5550112") > 0.80

    # Soundex
    assert soundex("Smith") == soundex("Smythe")
    assert soundex("Hamilton") == soundex("Hamiltone")
    assert soundex("Robert") == soundex("Rupert")


def test_compute_patient_match_score(empi_test_patients):
    """Verify scoring engine generates appropriate confidence levels and grades."""
    p1, p2, p3, p4 = empi_test_patients

    # Identical record
    score_self, _, grade_self = empi_service.compute_patient_match_score(p1, p1)
    assert score_self == 1.0
    assert grade_self == "exact"

    # High-confidence duplicate (p1 & p2)
    score_p2, feats_p2, grade_p2 = empi_service.compute_patient_match_score(p1, p2)
    assert score_p2 >= 0.85
    assert grade_p2 in ["exact", "probable"]
    assert feats_p2["dob_score"] == 1.0

    # Probable/possible duplicate (p1 & p3)
    score_p3, feats_p3, grade_p3 = empi_service.compute_patient_match_score(p1, p3)
    assert score_p3 >= 0.65
    assert grade_p3 in ["probable", "possible"]

    # Distinct non-match (p1 & p4)
    score_p4, _, grade_p4 = empi_service.compute_patient_match_score(p1, p4)
    assert score_p4 < 0.65
    assert grade_p4 == "distinct"


def test_find_candidate_matches(db_session, empi_test_patients):
    """Test searching candidates for identity resolution."""
    p1 = empi_test_patients[0]
    res = empi_service.find_candidate_matches(db_session, p1.patient_id, threshold=0.50)

    assert res.query_patient_id == p1.patient_id
    assert res.total_candidates >= 2
    # Highest ranked match should be p2
    assert res.candidates[0].patient_id == "PAT-EMPI-002"
    assert res.candidates[0].match_score >= 0.85


def test_link_and_unlink_lifecycle(db_session, empi_test_patients):
    """Test manual and automatic identity linking and unlinking."""
    p1, p2 = empi_test_patients[0], empi_test_patients[1]

    # Create master identity
    ident = empi_service.get_or_create_enterprise_identity(db_session, p1, user_id=1)
    assert ident.enterprise_id.startswith("EUID-")

    # Link second record
    link_res = empi_service.link_patient_record(
        db=db_session,
        enterprise_id=ident.enterprise_id,
        patient_id=p2.patient_id,
        user_id=1,
    )
    assert link_res.enterprise_id == ident.enterprise_id
    assert link_res.patient_id == p2.patient_id

    # Unlink
    unlinked = empi_service.unlink_patient_record(db_session, p2.patient_id, user_id=1)
    assert unlinked is True


def test_merge_and_split_identities(db_session, empi_test_patients):
    """Test merging duplicate identities and reverting/splitting them."""
    p1, p2 = empi_test_patients[0], empi_test_patients[1]

    merge_res = empi_service.merge_patient_identities(
        db=db_session,
        target_patient_id=p1.patient_id,
        source_patient_id=p2.patient_id,
        user_id=1,
        reason="Duplicate registration at Satellite Clinic",
    )
    assert merge_res.merge_id.startswith("MRG-")
    assert merge_res.target_patient_id == p1.patient_id
    assert merge_res.source_patient_id == p2.patient_id

    # Revert / Split
    split_ok = empi_service.split_patient_identity(
        db=db_session,
        merge_id=merge_res.merge_id,
        user_id=1,
    )
    assert split_ok is True


def test_empi_api_endpoints(client: TestClient, db_session: Session, empi_test_patients, test_doctor_user):
    """Verify REST endpoints for EMPI candidates, linking, reviews, and FHIR $match."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_doctor_user.id, role=test_doctor_user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    p1 = empi_test_patients[0]

    # 1. Candidates query
    resp = client.get(f"/api/v1/empi/match/candidates/{p1.patient_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["query_patient_id"] == p1.patient_id
    assert len(data["candidates"]) >= 2

    # 2. Link endpoint
    link_resp = client.post(
        "/api/v1/empi/link",
        headers=headers,
        json={
            "target_patient_id": p1.patient_id,
            "patient_id": "PAT-EMPI-002",
            "link_type": "manual_link",
        },
    )
    assert link_resp.status_code == 200
    link_data = link_resp.json()
    assert link_data["patient_id"] == "PAT-EMPI-002"

    # 3. Reviews list
    rev_resp = client.get("/api/v1/empi/reviews", headers=headers)
    assert rev_resp.status_code == 200

    # 4. FHIR $match
    fhir_resp = client.post(
        "/api/v1/empi/fhir/$match",
        headers=headers,
        json={
            "resource": {
                "resourceType": "Patient",
                "name": [{"family": "Hamilton", "given": ["Alexander"]}],
            },
            "count": 5,
        },
    )
    assert fhir_resp.status_code == 200
    fhir_data = fhir_resp.json()
    assert fhir_data["resourceType"] == "Bundle"
    assert fhir_data["type"] == "searchset"
    assert fhir_data["total"] >= 1

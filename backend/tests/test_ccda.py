"""Unit and Integration Tests for HL7 C-CDA R2.1 Generation, Parsing, and Security."""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.schemas.patient import Gender, PatientStatus
from app.services.ccda_service import ccda_service, parse_xml_safely


@pytest.fixture
def ccda_patient(db_session: Session):
    """Create a test patient for C-CDA document generation."""
    p = Patient(
        patient_id="PAT-CCDA-001",
        first_name="Benjamin",
        last_name="Franklin",
        date_of_birth=date(1970, 1, 17),
        gender=Gender.MALE,
        email="ben.franklin@example.com",
        phone="+1-555-0199",
        address="36 Market St, Philadelphia, PA",
        emergency_contact_name="Deborah Franklin",
        emergency_contact_phone="+1-555-0198",
        status=PatientStatus.ACTIVE,
        facility_id="FAC-001",
    )
    db_session.add(p)
    db_session.commit()
    return p


def test_ccda_export_generation(db_session, ccda_patient):
    """Verify C-CDA XML generation includes valid headers and clinical sections."""
    res = ccda_service.export_ccda_document(
        db=db_session,
        patient_id=ccda_patient.patient_id,
        document_type="continuity_of_care_document",
        user_id=1,
    )
    assert res.document_id.startswith("CCDA-")
    assert res.patient_id == ccda_patient.patient_id
    assert res.section_count >= 5
    assert len(res.sha256_hash) == 64

    # Verify XML content structure
    xml = res.xml_content
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert '<ClinicalDocument xmlns="urn:hl7-org:v3"' in xml
    assert '2.16.840.1.113883.10.20.22.1.2' in xml  # CCD Template ID
    assert 'Franklin' in xml
    assert 'Benjamin' in xml
    assert 'Active Problems and Conditions' in xml
    assert 'Allergies and Adverse Reactions' in xml
    assert 'Medications' in xml
    assert 'Vital Signs' in xml


def test_ccda_import_parsing(db_session, ccda_patient):
    """Test round-trip export-import fidelity."""
    export_res = ccda_service.export_ccda_document(
        db=db_session,
        patient_id=ccda_patient.patient_id,
        user_id=1,
    )

    import_res = ccda_service.import_ccda_document(
        db=db_session,
        patient_id=ccda_patient.patient_id,
        xml_content=export_res.xml_content,
        source_facility="Penn Health System",
        user_id=1,
    )
    assert import_res.document_id.startswith("CCDA-IMP-")
    assert import_res.patient_id == ccda_patient.patient_id
    assert import_res.problems_count >= 1
    assert import_res.allergies_count >= 1
    assert import_res.medications_count >= 1
    assert len(import_res.sections) >= 5


def test_xxe_protection():
    """Verify parser strictly rejects XML containing malicious entity/DOCTYPE attacks."""
    malicious_xxe_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
    <ClinicalDocument xmlns="urn:hl7-org:v3">
        <title>&xxe;</title>
    </ClinicalDocument>
    """
    with pytest.raises(ValueError, match="Forbidden XML constructs"):
        parse_xml_safely(malicious_xxe_xml)

    malformed_xml = "<ClinicalDocument><unclosed_tag></ClinicalDocument>"
    with pytest.raises(ValueError, match="Malformed C-CDA XML"):
        parse_xml_safely(malformed_xml)


def test_ccda_endpoints(client: TestClient, db_session: Session, ccda_patient, test_doctor_user):
    """Test C-CDA export, download, and import HTTP endpoints."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_doctor_user.id, role=test_doctor_user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Export
    exp_resp = client.post(
        "/api/v1/ccda/export",
        headers=headers,
        json={
            "patient_id": ccda_patient.patient_id,
            "document_type": "continuity_of_care_document",
        },
    )
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["patient_id"] == ccda_patient.patient_id
    xml_content = exp_data["xml_content"]

    # 2. Raw XML Download
    raw_resp = client.get(f"/api/v1/ccda/export/{ccda_patient.patient_id}/xml", headers=headers)
    assert raw_resp.status_code == 200
    assert "application/xml" in raw_resp.headers.get("content-type", "")

    # 3. Ingestion / Import
    imp_resp = client.post(
        "/api/v1/ccda/import",
        headers=headers,
        json={
            "patient_id": ccda_patient.patient_id,
            "xml_content": xml_content,
            "source_facility": "External Health Network",
        },
    )
    assert imp_resp.status_code == 200
    imp_data = imp_resp.json()
    assert imp_data["allergies_count"] >= 1
    assert imp_data["problems_count"] >= 1

    # 4. List document exchanges
    docs_resp = client.get(f"/api/v1/ccda/documents?patient_id={ccda_patient.patient_id}", headers=headers)
    assert docs_resp.status_code == 200
    assert docs_resp.json()["total"] >= 2

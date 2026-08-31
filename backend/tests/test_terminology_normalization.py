"""Unit & Integration Tests for Clinical Terminology Normalization and Cross-Walks."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.terminology_service import terminology_service


def test_normalize_loinc_lab_tests(client: TestClient):
    """Verifies normalization of laboratory terms to LOINC codes."""
    # 1. Potassium
    resp = client.post(
        "/api/v1/terminology/normalize",
        json={"query": "Serum Potassium", "target_system": "LOINC"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["normalized"]["system"] == "LOINC"
    assert data["normalized"]["code"] == "6298-4"
    assert data["normalized"]["confidence"] >= 0.85

    # 2. Hemoglobin A1c
    a1c_resp = client.post(
        "/api/v1/terminology/normalize",
        json={"query": "HbA1c level", "target_system": "LOINC"},
    )
    assert a1c_resp.status_code == 200
    a1c_data = a1c_resp.json()
    assert a1c_data["normalized"]["code"] == "4548-4"


def test_normalize_snomed_conditions(client: TestClient):
    """Verifies normalization of clinical diagnoses to SNOMED CT."""
    resp = client.post(
        "/api/v1/terminology/normalize",
        json={"query": "Type 2 Diabetes Mellitus", "target_system": "SNOMED_CT"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["normalized"]["system"] == "SNOMED_CT"
    assert data["normalized"]["code"] == "44054006"


def test_normalize_rxnorm_medications(client: TestClient):
    """Verifies normalization of medication names to RxNorm concepts."""
    resp = client.post(
        "/api/v1/terminology/normalize",
        json={"query": "Lisinopril 10mg tablet", "target_system": "RXNORM"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["normalized"]["system"] == "RXNORM"
    assert data["normalized"]["code"] == "314076"


def test_vocabulary_crosswalk_icd10_to_snomed(client: TestClient):
    """Verifies cross-walk translation between ICD-10 and SNOMED CT."""
    resp = client.post(
        "/api/v1/terminology/crosswalk",
        json={
            "source_system": "ICD10",
            "source_code": "E11.9",
            "target_system": "SNOMED_CT",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "MATCHED"
    assert data["target_code"] == "44054006"
    assert "Type 2 diabetes" in data["target_display"]


def test_unmapped_terminology_fallback(client: TestClient):
    """Verifies unmapped clinical query fallback handling."""
    resp = client.post(
        "/api/v1/terminology/normalize",
        json={"query": "ExtremelyUnusualCustomUnknownConditionXYZ"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NO_MATCH"
    assert data["normalized"]["code"] == "UNMAPPED"

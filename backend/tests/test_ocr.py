"""Tests for Pluggable OCR Subsystem and Scanned PDF Ingestion.

Phase 8.8: Pluggable OCR Subsystem for Scanned/Image Medical Documents.
"""

import io
import os
import tempfile
from fastapi import status
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

from app.ai.extractors import extract_document_text, extract_pdf
from app.ai.ocr import (
    BaseOCRProvider,
    MockOCRProvider,
    TextractOCRProvider,
    get_ocr_provider,
)
from app.core.config import settings
from app.schemas.user import UserRole


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def create_scanned_pdf_file(metadata_subject: str = "") -> str:
    """Create a temporary PDF file with no direct text layer (simulating scanned image)."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    if metadata_subject:
        writer.add_metadata({"/Subject": metadata_subject})

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    writer.write(tmp)
    tmp.close()
    return tmp.name


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.ADMIN,
    email: str = "admin_ocr@hospital.org",
    name: str = "Admin OCR",
) -> tuple[dict[str, str], int]:
    """Register and login helper returning authorization headers and user ID."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "role": role.value,
        },
    )
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


def test_ocr_provider_factory():
    """Verify get_ocr_provider returns correct provider instances."""
    mock_prov = get_ocr_provider("mock")
    assert isinstance(mock_prov, MockOCRProvider)
    assert isinstance(mock_prov, BaseOCRProvider)

    textract_prov = get_ocr_provider("textract")
    assert isinstance(textract_prov, TextractOCRProvider)

    with pytest.raises(ValueError, match="Unsupported OCR provider"):
        get_ocr_provider("unsupported_ocr_engine")


def test_mock_ocr_provider_extraction():
    """Verify MockOCRProvider extracts text from scanned PDF and preserves page numbers."""
    pdf_path = create_scanned_pdf_file(metadata_subject="Scanned Lab Report: Potassium 4.2 mEq/L")
    try:
        prov = MockOCRProvider()
        extracted = prov.extract_text(pdf_path, ".pdf")
        assert extracted.page_count == 1
        assert len(extracted.pages) == 1
        assert extracted.pages[0][0] == 1  # page_number
        assert "potassium 4.2" in extracted.text.lower()
        assert extracted.metadata.get("ocr") is True
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_scanned_pdf_rejected_when_ocr_disabled(monkeypatch):
    """When OCR_ENABLED=False, scanned PDFs with no text stream must raise ValueError."""
    monkeypatch.setattr(settings, "OCR_ENABLED", False)
    pdf_path = create_scanned_pdf_file(metadata_subject="")
    try:
        with pytest.raises(ValueError, match="contains no extractable text"):
            extract_pdf(pdf_path)
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_scanned_pdf_processed_when_ocr_enabled(monkeypatch):
    """When OCR_ENABLED=True, scanned PDFs are automatically routed through OCR."""
    monkeypatch.setattr(settings, "OCR_ENABLED", True)
    monkeypatch.setattr(settings, "OCR_PROVIDER", "mock")

    pdf_path = create_scanned_pdf_file(metadata_subject="Scanned ECG: Normal Sinus Rhythm")
    try:
        extracted = extract_pdf(pdf_path)
        assert extracted.page_count == 1
        assert "normal sinus rhythm" in extracted.text.lower()
        assert extracted.metadata.get("ocr") is True
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# ---------------------------------------------------------------------------
# End-to-End API Integration Tests with OCR
# ---------------------------------------------------------------------------


def test_e2e_scanned_pdf_upload_and_indexing_with_ocr(client: TestClient, monkeypatch):
    """End-to-end test of scanned PDF upload, OCR processing, chunking, and ChromaDB vector indexing."""
    monkeypatch.setattr(settings, "OCR_ENABLED", True)
    monkeypatch.setattr(settings, "OCR_PROVIDER", "mock")

    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_ocr_e2e@hospital.org", name="Admin OCR E2E"
    )

    # 1. Create Patient
    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Oliver",
            "last_name": "Scan",
            "date_of_birth": "1965-04-10",
            "gender": "male",
            "email": "oliver_ocr@patient.org",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    # 2. Generate scanned PDF bytes
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Subject": "PATHOLOGY REPORT: Biopsy reveals benign tissue."})
    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()

    # 3. Upload Document
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("scanned_biopsy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={
            "patient_id": patient_id,
            "title": "Scanned Pathology Report",
            "document_type": "lab_report",
        },
        headers=admin_headers,
    )
    assert upload_res.status_code == status.HTTP_201_CREATED
    doc_data = upload_res.json()
    assert doc_data["processing_status"] == "completed"
    assert doc_data["total_chunks"] >= 1

    # 4. Execute RAG Query against OCR-extracted document
    rag_res = client.post(
        "/api/v1/rag/query",
        json={"patient_id": patient_id, "query": "What did the biopsy reveal?"},
        headers=admin_headers,
    )
    assert rag_res.status_code == status.HTTP_200_OK
    rag_data = rag_res.json()
    assert "benign" in rag_data["answer"].lower()
    assert len(rag_data["citations"]) >= 1

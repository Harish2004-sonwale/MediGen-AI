"""
Tests for Phase 8.4: Vector indexing service integration.

Uses SQLite in-memory DB (from conftest.py) + temporary ChromaDB directory.

Covers:
- Chunk → embedding → vector_id saved to database
- document total_chunks consistency
- Repeated indexing (idempotency) does not create duplicate vectors
- Reprocessing removes old vectors before inserting new ones
- Deletion removes vectors from ChromaDB
- Failure handling when no chunks exist
- No medical content appears in log output
"""

import io
import logging
import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.ai.embeddings import MockEmbeddingProvider
from app.ai.vector_store import ChromaVectorStore
from app.models.document import DocumentChunk, MedicalDocument
from app.schemas.document import DocumentProcessingStatus, DocumentType
from app.services.vector_indexing_service import (
    build_vector_metadata,
    index_document_chunks,
    remove_document_vectors,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_document(db_session, patient) -> MedicalDocument:
    """Create a minimal MedicalDocument in the in-memory DB."""
    doc = MedicalDocument(
        document_id="DOCU-TEST-0001",
        patient_id=patient.id,
        uploader_user_id=None,
        encounter_id=None,
        title="Test Clinical Note",
        document_type=DocumentType.CLINICAL_NOTE,
        original_filename="test.txt",
        file_extension=".txt",
        file_size_bytes=100,
        storage_path="/tmp/test.txt",
        mime_type="text/plain",
        processing_status=DocumentProcessingStatus.PROCESSING,
        total_chunks=0,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def _add_chunks(db_session, document: MedicalDocument, patient, texts: list[str]) -> list[DocumentChunk]:
    chunks = []
    for i, text in enumerate(texts):
        chunk = DocumentChunk(
            chunk_id=f"CHK-TEST-{i:04d}",
            document_id=document.id,
            patient_id=patient.id,
            chunk_index=i,
            page_number=1,
            content=text,
            token_count=len(text.split()),
            vector_id=None,
        )
        db_session.add(chunk)
        chunks.append(chunk)
    db_session.commit()
    for c in chunks:
        db_session.refresh(c)
    return chunks


@pytest.fixture()
def tmp_store() -> ChromaVectorStore:
    import uuid
    return ChromaVectorStore(db_path=None, collection_name=f"test_index_{uuid.uuid4().hex}")




@pytest.fixture()
def embedding_provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider(dimension=64)


# ---------------------------------------------------------------------------
# Patient fixture (re-creates minimal patient inline to avoid heavy fixture chain)
# ---------------------------------------------------------------------------


def _make_patient(db_session):
    """Insert a minimal patient for FK constraints."""
    from datetime import date
    from app.models.patient import Patient
    from app.schemas.patient import Gender, PatientStatus

    import secrets
    pat = Patient(
        patient_id=f"PAT-TEST-{secrets.token_hex(2).upper()}",
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 1),
        gender=Gender.MALE,
        email=f"testpatient_{secrets.token_hex(4)}@example.com",
        phone="9999999999",
        address="123 Test Street",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(pat)
    db_session.commit()
    db_session.refresh(pat)
    return pat


# ---------------------------------------------------------------------------
# build_vector_metadata
# ---------------------------------------------------------------------------


def test_build_vector_metadata_fields(db_session):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    chunks = _add_chunks(db_session, doc, patient, ["Sample clinical text."])
    chunk = chunks[0]

    meta = build_vector_metadata(chunk=chunk, document=doc)

    assert meta["patient_id"] == str(doc.patient_id)
    assert meta["document_id"] == doc.document_id
    assert meta["chunk_id"] == chunk.chunk_id
    assert meta["chunk_index"] == chunk.chunk_index
    assert meta["document_type"] == "clinical_note"
    assert "page_number" in meta


# ---------------------------------------------------------------------------
# index_document_chunks: vector_id persistence
# ---------------------------------------------------------------------------


def test_index_document_chunks_saves_vector_ids(db_session, tmp_store, embedding_provider):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    texts = [
        "Patient presents with chest tightness and shortness of breath.",
        "ECG shows normal sinus rhythm.",
        "Recommend stress test and echocardiogram.",
    ]
    chunks = _add_chunks(db_session, doc, patient, texts)

    updated_doc = index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )

    assert updated_doc.processing_status == DocumentProcessingStatus.COMPLETED
    assert updated_doc.total_chunks == len(texts)

    # All chunks should now have non-null vector_id
    db_session.expire_all()
    db_chunks = list(
        db_session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        ).all()
    )
    assert len(db_chunks) == len(texts)
    for chunk in db_chunks:
        assert chunk.vector_id is not None, f"Chunk {chunk.chunk_id} missing vector_id."


def test_index_document_chunks_vector_count_in_store(db_session, tmp_store, embedding_provider):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    texts = ["First chunk.", "Second chunk."]
    _add_chunks(db_session, doc, patient, texts)

    index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )

    assert tmp_store.count(patient_id=str(patient.id)) == 2


def test_index_document_chunks_no_chunks_marks_failed(db_session, tmp_store, embedding_provider):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    # No chunks added

    updated_doc = index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )

    assert updated_doc.processing_status == DocumentProcessingStatus.FAILED
    assert "No chunks" in (updated_doc.error_message or "")


# ---------------------------------------------------------------------------
# Idempotency: repeated indexing must not duplicate vectors
# ---------------------------------------------------------------------------


def test_repeated_indexing_does_not_duplicate_vectors(db_session, tmp_store, embedding_provider):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    texts = ["Blood pressure 130/80 mmHg.", "Temperature 37.2°C."]
    _add_chunks(db_session, doc, patient, texts)

    # First indexing
    index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )
    count_after_first = tmp_store.count()

    # Second indexing (same chunks, upsert should overwrite, not duplicate)
    index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )
    count_after_second = tmp_store.count()

    assert count_after_second == count_after_first, (
        f"Repeated indexing created duplicates: {count_after_first} → {count_after_second}"
    )


# ---------------------------------------------------------------------------
# remove_document_vectors
# ---------------------------------------------------------------------------


def test_remove_document_vectors_cleans_store(db_session, tmp_store, embedding_provider):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    _add_chunks(db_session, doc, patient, ["Clinical finding: oedema bilateral lower limbs."])

    index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=embedding_provider,
        vector_store=tmp_store,
    )
    assert tmp_store.count() == 1

    removed = remove_document_vectors(document=doc, vector_store=tmp_store)
    assert removed == 1
    assert tmp_store.count() == 0


def test_remove_document_vectors_nonexistent_is_noop(db_session, tmp_store):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    # No vectors indexed; should return 0 gracefully
    removed = remove_document_vectors(document=doc, vector_store=tmp_store)
    assert removed == 0


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_index_document_chunks_handles_embedding_failure(db_session, tmp_store):
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    _add_chunks(db_session, doc, patient, ["Some chunk text."])

    # Mock provider that raises
    bad_provider = MagicMock()
    bad_provider.embed_documents.side_effect = RuntimeError("Embedding API unavailable")

    updated_doc = index_document_chunks(
        db=db_session,
        document=doc,
        embedding_provider=bad_provider,
        vector_store=tmp_store,
    )

    assert updated_doc.processing_status == DocumentProcessingStatus.FAILED
    assert updated_doc.error_message is not None


# ---------------------------------------------------------------------------
# No medical content in log output — security test
# ---------------------------------------------------------------------------


def test_indexing_does_not_log_chunk_content(db_session, tmp_store, embedding_provider):
    """Chunk content must never appear in log output."""
    patient = _make_patient(db_session)
    doc = _make_document(db_session, patient)
    secret_text = "CONFIDENTIAL_CLINICAL_DATA_XK7Q2"
    _add_chunks(db_session, doc, patient, [secret_text])

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    root_logger = logging.getLogger("app")
    root_logger.addHandler(handler)

    try:
        index_document_chunks(
            db=db_session,
            document=doc,
            embedding_provider=embedding_provider,
            vector_store=tmp_store,
        )
    finally:
        root_logger.removeHandler(handler)

    log_output = log_capture.getvalue()
    assert secret_text not in log_output, (
        "SECURITY VIOLATION: Chunk content was found in log output!"
    )

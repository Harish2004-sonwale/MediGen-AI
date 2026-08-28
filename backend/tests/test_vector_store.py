"""
Tests for Phase 8.4: ChromaVectorStore.

Uses an in-memory or temporary ChromaDB collection so no persistent
data is written to the project directory during testing.

Covers:
- Collection initialisation
- Upsert and count
- Similarity search with top_k
- patient_id metadata filtering (isolation between patients)
- document_id filtering
- document_type filtering
- delete_by_document removes correct vectors
- health_check returns healthy status
- Missing patient_id raises ValueError (cross-patient search forbidden)
- Patient A cannot retrieve Patient B chunks — SECURITY CRITICAL
"""

import os
import tempfile
from typing import Generator

import pytest

from app.ai.embeddings import MockEmbeddingProvider
from app.ai.vector_store import ChromaVectorStore, VectorSearchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_vector_store() -> ChromaVectorStore:
    """Create an in-memory ChromaVectorStore with a unique collection for fast, isolated testing."""
    import uuid
    return ChromaVectorStore(db_path=None, collection_name=f"test_col_{uuid.uuid4().hex}")




@pytest.fixture()
def provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider(dimension=64)


def make_embedding(provider: MockEmbeddingProvider, text: str) -> list[float]:
    return provider.embed_query(text)


# ---------------------------------------------------------------------------
# Basic operations
# ---------------------------------------------------------------------------


def test_vector_store_initialises(tmp_vector_store):
    health = tmp_vector_store.health_check()
    assert health["healthy"] is True
    assert health["collection_name"] == tmp_vector_store._collection_name
    assert "vector_count" in health



def test_vector_store_count_empty(tmp_vector_store):
    assert tmp_vector_store.count() == 0


def test_vector_store_upsert_and_count(tmp_vector_store, provider):
    embeddings = provider.embed_documents(["Clinical note: patient stable.", "Lab: Hb 12.4 g/dL."])
    metadatas = [
        {"patient_id": "P-001", "document_id": "DOCU-001", "chunk_id": "CHK-001", "chunk_index": 0, "page_number": 1, "document_type": "clinical_note"},
        {"patient_id": "P-001", "document_id": "DOCU-001", "chunk_id": "CHK-002", "chunk_index": 1, "page_number": 1, "document_type": "clinical_note"},
    ]
    tmp_vector_store.upsert(
        vector_ids=["CHK-001", "CHK-002"],
        embeddings=embeddings,
        metadatas=metadatas,
        documents=["Clinical note: patient stable.", "Lab: Hb 12.4 g/dL."],
    )
    assert tmp_vector_store.count() == 2


def test_vector_store_upsert_empty_is_noop(tmp_vector_store):
    # Should not raise
    tmp_vector_store.upsert(vector_ids=[], embeddings=[], metadatas=[], documents=[])
    assert tmp_vector_store.count() == 0


def test_upsert_without_patient_id_raises(tmp_vector_store, provider):
    emb = provider.embed_documents(["Some text."])
    bad_meta = [{"document_id": "DOC-001", "chunk_id": "CHK-X"}]  # no patient_id
    with pytest.raises(ValueError, match="patient_id"):
        tmp_vector_store.upsert(
            vector_ids=["CHK-X"],
            embeddings=emb,
            metadatas=bad_meta,
            documents=["Some text."],
        )


# ---------------------------------------------------------------------------
# Similarity search
# ---------------------------------------------------------------------------


def _seed_two_patients(store: ChromaVectorStore, provider: MockEmbeddingProvider) -> None:
    """Seed vectors for two patients with distinct clinical content."""
    texts_a = [
        "Patient A: Diagnosis hypertension, on amlodipine 5 mg.",
        "Patient A: Blood pressure 150/90 mmHg at rest.",
    ]
    texts_b = [
        "Patient B: Diagnosis Type 2 Diabetes, HbA1c 8.2%.",
        "Patient B: Fasting glucose 210 mg/dL.",
    ]

    embs_a = provider.embed_documents(texts_a)
    embs_b = provider.embed_documents(texts_b)

    meta_a = [
        {"patient_id": "P-001", "document_id": "DOCU-A1", "chunk_id": "CHK-A1", "chunk_index": 0, "page_number": 1, "document_type": "clinical_note"},
        {"patient_id": "P-001", "document_id": "DOCU-A1", "chunk_id": "CHK-A2", "chunk_index": 1, "page_number": 1, "document_type": "clinical_note"},
    ]
    meta_b = [
        {"patient_id": "P-002", "document_id": "DOCU-B1", "chunk_id": "CHK-B1", "chunk_index": 0, "page_number": 1, "document_type": "lab_report"},
        {"patient_id": "P-002", "document_id": "DOCU-B1", "chunk_id": "CHK-B2", "chunk_index": 1, "page_number": 1, "document_type": "lab_report"},
    ]

    store.upsert(
        vector_ids=["CHK-A1", "CHK-A2"],
        embeddings=embs_a,
        metadatas=meta_a,
        documents=texts_a,
    )
    store.upsert(
        vector_ids=["CHK-B1", "CHK-B2"],
        embeddings=embs_b,
        metadatas=meta_b,
        documents=texts_b,
    )


def test_similarity_search_basic(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("blood pressure medication")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-001",
        top_k=5,
    )
    assert len(results) > 0
    assert all(isinstance(r, VectorSearchResult) for r in results)
    assert all(r.patient_id == "P-001" for r in results)


def test_similarity_search_patient_isolation_security(tmp_vector_store, provider):
    """SECURITY: Patient A query must NEVER return Patient B chunks."""
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("diabetes glucose insulin")
    # Query scoped to Patient A even though Patient B has more relevant content
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-001",
        top_k=10,
    )
    returned_patient_ids = {r.patient_id for r in results}
    assert "P-002" not in returned_patient_ids, (
        "SECURITY VIOLATION: Patient B chunks were returned in Patient A's search!"
    )


def test_similarity_search_returns_only_patient_b_when_scoped(tmp_vector_store, provider):
    """Patient B search must not return Patient A chunks."""
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("hypertension blood pressure amlodipine")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-002",
        top_k=10,
    )
    returned_patient_ids = {r.patient_id for r in results}
    assert "P-001" not in returned_patient_ids, (
        "SECURITY VIOLATION: Patient A chunks were returned in Patient B's search!"
    )


def test_similarity_search_top_k_limit(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("clinical report")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-001",
        top_k=1,
    )
    assert len(results) <= 1


def test_similarity_search_document_id_filter(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("patient clinical")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-001",
        document_id="DOCU-A1",
        top_k=5,
    )
    assert all(r.document_id == "DOCU-A1" for r in results)


def test_similarity_search_document_type_filter(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("lab glucose test")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-002",
        document_type="lab_report",
        top_k=5,
    )
    assert all(r.document_type == "lab_report" for r in results)


def test_similarity_search_empty_patient_id_raises(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("any query")
    with pytest.raises(ValueError, match="patient_id is required"):
        tmp_vector_store.similarity_search(
            query_embedding=query_emb,
            patient_id="",
            top_k=5,
        )


def test_similarity_search_unknown_patient_returns_empty(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    query_emb = provider.embed_query("any query")
    results = tmp_vector_store.similarity_search(
        query_embedding=query_emb,
        patient_id="P-UNKNOWN",
        top_k=5,
    )
    assert results == []


# ---------------------------------------------------------------------------
# Count with patient filter
# ---------------------------------------------------------------------------


def test_count_by_patient(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    assert tmp_vector_store.count(patient_id="P-001") == 2
    assert tmp_vector_store.count(patient_id="P-002") == 2
    assert tmp_vector_store.count() == 4


# ---------------------------------------------------------------------------
# Delete operations
# ---------------------------------------------------------------------------


def test_delete_by_document_removes_correct_vectors(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    assert tmp_vector_store.count() == 4

    deleted = tmp_vector_store.delete_by_document(document_id="DOCU-A1")
    assert deleted == 2
    assert tmp_vector_store.count() == 2
    # Patient B's vectors must remain
    assert tmp_vector_store.count(patient_id="P-002") == 2
    assert tmp_vector_store.count(patient_id="P-001") == 0


def test_delete_by_document_nonexistent_is_noop(tmp_vector_store):
    deleted = tmp_vector_store.delete_by_document(document_id="DOCU-DOES-NOT-EXIST")
    assert deleted == 0


def test_delete_by_vector_ids(tmp_vector_store, provider):
    _seed_two_patients(tmp_vector_store, provider)
    deleted = tmp_vector_store.delete_by_vector_ids(vector_ids=["CHK-A1"])
    assert deleted == 1
    assert tmp_vector_store.count() == 3


def test_delete_by_vector_ids_empty_is_noop(tmp_vector_store):
    deleted = tmp_vector_store.delete_by_vector_ids(vector_ids=[])
    assert deleted == 0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check_structure(tmp_vector_store):
    result = tmp_vector_store.health_check()
    assert result["healthy"] is True
    assert "collection_name" in result
    assert "vector_count" in result
    assert "provider" in result
    # Must NOT expose db_path in the returned dict
    # Check that no key named "path", "db_path", or "storage_path" is present
    for key in result.keys():
        assert "path" not in key.lower(), f"Health check must not expose filesystem path keys. Found: {key}"
    assert "db_path" not in result

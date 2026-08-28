"""
Tests for Phase 8.4: Embedding provider abstraction.

Covers:
- MockEmbeddingProvider determinism (same text → same vector, cross-process stable)
- Fixed dimension
- Different texts produce different vectors
- Batch embedding consistency
- Query embedding consistency with document embedding
- L2 normalisation (vectors are unit-length)
- get_embedding_provider factory
- Unknown provider raises ValueError
"""

import math
import pytest

from app.ai.embeddings import (
    BaseEmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)


# ---------------------------------------------------------------------------
# MockEmbeddingProvider: determinism and dimension
# ---------------------------------------------------------------------------


def test_mock_embedding_fixed_dimension():
    provider = MockEmbeddingProvider(dimension=384)
    vec = provider.embed_query("Patient has hypertension and diabetes mellitus.")
    assert len(vec) == 384


def test_mock_embedding_custom_dimension():
    provider = MockEmbeddingProvider(dimension=128)
    vec = provider.embed_query("Blood pressure 140/90 mmHg.")
    assert len(vec) == 128


def test_mock_embedding_deterministic_same_text():
    """Same text must always produce the same vector (process-stable via hashlib)."""
    provider = MockEmbeddingProvider(dimension=384)
    text = "Serum creatinine 1.2 mg/dL — within normal range."
    v1 = provider.embed_query(text)
    v2 = provider.embed_query(text)
    assert v1 == v2, "Same input text must yield identical embeddings."


def test_mock_embedding_different_texts_produce_different_vectors():
    """Different texts must produce meaningfully different vectors."""
    provider = MockEmbeddingProvider(dimension=384)
    v1 = provider.embed_query("Patient has cardiac arrhythmia.")
    v2 = provider.embed_query("Haemoglobin A1c 7.2% — good glycaemic control.")
    assert v1 != v2, "Different texts must produce different embeddings."


def test_mock_embedding_vectors_are_unit_normalised():
    """Vectors should be approximately L2-unit-normalised for cosine similarity."""
    provider = MockEmbeddingProvider(dimension=384)
    vec = provider.embed_query("Troponin I elevated at 0.5 ng/mL.")
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-6, f"Vector norm should be ~1.0, got {norm}."


def test_mock_embedding_batch_matches_individual():
    """Batch embedding must produce same vectors as individual calls."""
    provider = MockEmbeddingProvider(dimension=384)
    texts = [
        "Fever 38.9°C, tachycardia HR 110 bpm.",
        "Discharge summary: patient stable.",
        "Prescription: metformin 500 mg twice daily.",
    ]
    batch = provider.embed_documents(texts)
    for text, batch_vec in zip(texts, batch):
        individual_vec = provider.embed_query(text)
        assert batch_vec == individual_vec, f"Batch and individual embedding differ for: '{text[:30]}...'"


def test_mock_embedding_empty_batch():
    provider = MockEmbeddingProvider(dimension=384)
    result = provider.embed_documents([])
    assert result == []


def test_mock_embedding_is_base_provider_subclass():
    provider = MockEmbeddingProvider(dimension=384)
    assert isinstance(provider, BaseEmbeddingProvider)


def test_mock_embedding_dimension_property():
    provider = MockEmbeddingProvider(dimension=256)
    assert provider.dimension == 256


def test_mock_embedding_invalid_dimension_raises():
    with pytest.raises(ValueError, match="dimension must be >= 1"):
        MockEmbeddingProvider(dimension=0)


# ---------------------------------------------------------------------------
# get_embedding_provider factory
# ---------------------------------------------------------------------------


def test_get_embedding_provider_mock():
    provider = get_embedding_provider(provider="mock", dimension=384)
    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.dimension == 384


def test_get_embedding_provider_mock_case_insensitive():
    provider = get_embedding_provider(provider="MOCK", dimension=128)
    assert isinstance(provider, MockEmbeddingProvider)


def test_get_embedding_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        get_embedding_provider(provider="openai_unknown_xyz", dimension=384)


# ---------------------------------------------------------------------------
# Cross-text distinctiveness sanity check
# ---------------------------------------------------------------------------


def test_mock_embedding_multiple_clinical_texts_all_distinct():
    """All 5 distinct clinical texts must produce 5 distinct vectors."""
    provider = MockEmbeddingProvider(dimension=384)
    texts = [
        "Diagnosis: Type 2 Diabetes Mellitus.",
        "ECG shows sinus tachycardia.",
        "Chest X-ray: bilateral pleural effusion.",
        "Medication: Aspirin 81 mg daily.",
        "Patient reports chest pain on exertion.",
    ]
    vectors = provider.embed_documents(texts)
    # Convert to tuples for hashing
    unique_vectors = {tuple(v) for v in vectors}
    assert len(unique_vectors) == len(texts), "Each distinct clinical text must produce a unique vector."

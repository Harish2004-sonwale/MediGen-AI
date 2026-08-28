"""
Embedding provider abstraction for MediGen AI clinical RAG pipeline.

Architecture:
    BaseEmbeddingProvider  (abstract interface)
    └── MockEmbeddingProvider  (deterministic, hashlib-based, no cloud deps)
    └── (future) OpenAIEmbeddingProvider
    └── (future) BedrockEmbeddingProvider

Design principles:
- Swap providers without changing RAG or indexing services.
- Never log chunk content or raw embeddings.
- MockEmbeddingProvider uses stable hashlib hashing (not Python's built-in
  hash()) so results are identical across processes and platforms.
"""

from __future__ import annotations

import hashlib
import math
import struct
from abc import ABC, abstractmethod
from typing import Sequence


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding providers.

    All concrete providers must implement:
    - embed_documents: batch embed a list of text strings
    - embed_query: embed a single query string

    The embedding dimension is exposed via the ``dimension`` property so
    the vector store can verify dimensionality compatibility at startup.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the fixed embedding vector dimension."""

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: Sequence of text strings to embed.

        Returns:
            List of float vectors, one per input text.
            All vectors share the same fixed dimension.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Generate an embedding for a single query string.

        Args:
            text: The query text to embed.

        Returns:
            A single float vector of fixed dimension.
        """


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic embedding provider for unit testing and CI.

    Key properties:
    - No network or API dependency.
    - Same input text always produces the same vector across processes
      (uses hashlib SHA-256, NOT Python built-in hash()).
    - Different texts produce meaningfully different vectors.
    - Vectors are L2-normalised to unit length (suitable for cosine similarity).
    - Fixed configurable dimension (default 384 to match common sentence models).

    Implementation strategy:
    1. Compute SHA-256 digest of the UTF-8 text.
    2. Expand digest bytes into ``dimension`` float components using a
       seeded deterministic scheme (repeating the digest with counter bytes).
    3. Normalise the resulting vector to unit L2 norm.
    """

    def __init__(self, dimension: int = 384) -> None:
        if dimension < 1:
            raise ValueError(f"Embedding dimension must be >= 1, got {dimension}.")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _text_to_vector(self, text: str) -> list[float]:
        """Convert text to a deterministic unit-normalised float vector."""
        # Produce a stable seed from text content
        raw_bytes = text.encode("utf-8", errors="replace")
        digest = hashlib.sha256(raw_bytes).digest()  # 32 bytes

        # Expand digest bytes to fill ``dimension`` floats
        components: list[float] = []
        idx = 0
        counter = 0
        while len(components) < self._dimension:
            # Use counter byte to differentiate successive 4-byte windows
            counter_byte = bytes([counter % 256])
            extended = hashlib.sha256(digest + counter_byte).digest()
            # Unpack as 8 unsigned integers (4 bytes each) → 8 floats per round
            n_available = min(8, self._dimension - len(components))
            for i in range(n_available):
                value = struct.unpack_from(">I", extended, i * 4)[0]
                # Map to [-1.0, 1.0]
                components.append((value / 0xFFFFFFFF) * 2.0 - 1.0)
            idx += 8
            counter += 1

        vec = components[: self._dimension]

        # L2-normalise for cosine similarity
        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-10:
            # Degenerate case — return uniform unit vector
            val = 1.0 / math.sqrt(self._dimension)
            return [val] * self._dimension

        return [v / norm for v in vec]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Deterministically embed a batch of document texts."""
        return [self._text_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        """Deterministically embed a single query text."""
        return self._text_to_vector(text)


def get_embedding_provider(provider: str = "mock", dimension: int = 384) -> BaseEmbeddingProvider:
    """Factory function to instantiate the configured embedding provider.

    Args:
        provider: Provider name from settings (e.g. "mock").
        dimension: Target embedding dimension.

    Returns:
        Configured BaseEmbeddingProvider instance.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    if provider.lower() == "mock":
        return MockEmbeddingProvider(dimension=dimension)
    raise ValueError(
        f"Unsupported embedding provider '{provider}'. "
        f"Supported providers: 'mock'. "
        f"To add a real provider, subclass BaseEmbeddingProvider and register it here."
    )

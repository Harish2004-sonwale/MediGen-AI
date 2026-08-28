"""
Vector store abstraction and ChromaDB implementation for MediGen AI.

Architecture:
    BaseVectorStore         (abstract interface)
    └── ChromaVectorStore   (ChromaDB local persistent store)
    └── (future) PgVectorStore
    └── (future) OpenSearchVectorStore

Design principles:
- Patient-level isolation is MANDATORY at the retrieval layer.
  Every similarity_search call REQUIRES a patient_id filter.
  Searches across patients are architecturally forbidden.
- Internal ChromaDB paths are never exposed in API responses.
- Metadata stored per vector: patient_id, document_id, chunk_id,
  chunk_index, page_number, document_type.
- The database remains the authoritative source for chunk content
  and metadata. ChromaDB is the retrieval/index layer only.
- Never log raw medical text or embedding vectors.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class VectorSearchResult:
    """A single result from a vector similarity search."""

    chunk_id: str
    document_id: str
    patient_id: str
    chunk_index: int
    page_number: Optional[int]
    document_type: str
    distance: float
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseVectorStore(ABC):
    """Abstract interface for vector store backends.

    All concrete implementations must enforce patient_id filtering on
    every similarity search call. Cross-patient retrieval is forbidden.
    """

    @abstractmethod
    def upsert(
        self,
        vector_ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        """Add or update vectors in the store.

        Args:
            vector_ids: Unique IDs for each vector (typically chunk_id).
            embeddings: List of embedding float vectors.
            metadatas: Metadata dicts, one per vector.
            documents: Associated text fragments (stored for reference).
        """

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: list[float],
        patient_id: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> list[VectorSearchResult]:
        """Find the most semantically similar chunks for a patient.

        IMPORTANT: patient_id is always required.  Omitting it is a
        programming error and implementations MUST reject it.

        Args:
            query_embedding: Query vector.
            patient_id: Required patient scope for isolation.
            top_k: Number of results to return.
            document_id: Optional further scope to a single document.
            document_type: Optional filter by document type.

        Returns:
            List of VectorSearchResult ordered by ascending distance.
        """

    @abstractmethod
    def delete_by_document(self, document_id: str) -> int:
        """Remove all vectors associated with a document_id.

        Returns:
            Number of vectors deleted.
        """

    @abstractmethod
    def delete_by_vector_ids(self, vector_ids: list[str]) -> int:
        """Remove vectors by their explicit vector IDs.

        Returns:
            Number of vectors deleted.
        """

    @abstractmethod
    def count(self, patient_id: Optional[str] = None) -> int:
        """Return total number of vectors, optionally scoped to a patient."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Verify connectivity and basic availability of the vector store.

        Returns:
            Dict with at minimum a ``healthy`` bool key.
            Must NOT expose internal filesystem paths.
        """


# ---------------------------------------------------------------------------
# ChromaDB implementation
# ---------------------------------------------------------------------------


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-backed persistent local vector store.

    Configuration:
        db_path: Directory for ChromaDB persistent storage.
        collection_name: Name of the Chroma collection to use.

    Patient isolation:
        Every upsert stores ``patient_id`` in the metadata.
        Every similarity_search applies a ``patient_id`` where-filter.
        This prevents cross-patient retrieval at the vector-store layer.

    Note:
        Internal db_path is never included in returned data.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: str = "medical_documents",
    ) -> None:
        self._db_path = db_path
        self._collection_name = collection_name
        self._client = None
        self._collection = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialise ChromaDB persistent or ephemeral client and collection."""
        try:
            import chromadb  # type: ignore

            if self._db_path is None or self._db_path == ":memory:":
                self._client = chromadb.EphemeralClient()
            else:
                self._client = chromadb.PersistentClient(path=self._db_path)

            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaVectorStore initialised [collection=%s, in_memory=%s]",
                self._collection_name,
                self._db_path is None or self._db_path == ":memory:",
            )
        except ImportError as exc:
            raise ImportError(
                "ChromaDB is not installed. Add 'chromadb' to requirements.txt."
            ) from exc
        except Exception as exc:
            logger.error("ChromaVectorStore initialisation failed: %s", type(exc).__name__)
            raise RuntimeError(f"Failed to initialise ChromaDB vector store: {exc}") from exc

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert(
        self,
        vector_ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        """Upsert vectors into the collection.

        All required patient isolation metadata must be present in each
        metadata dict before calling this method.
        """
        if not vector_ids:
            return

        for meta in metadatas:
            if "patient_id" not in meta:
                raise ValueError("All vector metadata MUST include 'patient_id' for patient isolation.")

        # ChromaDB upsert is idempotent — existing IDs are overwritten
        self._collection.upsert(
            ids=vector_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.debug("Upserted %d vectors into collection '%s'.", len(vector_ids), self._collection_name)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def similarity_search(
        self,
        query_embedding: list[float],
        patient_id: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> list[VectorSearchResult]:
        """Perform a patient-scoped similarity search.

        Raises:
            ValueError: If patient_id is empty — cross-patient search is forbidden.
        """
        if not patient_id or not patient_id.strip():
            raise ValueError(
                "patient_id is required for all vector similarity searches. "
                "Cross-patient retrieval is architecturally forbidden."
            )

        # Build ChromaDB where clause — patient_id is always required
        where: dict[str, Any] = {"patient_id": {"$eq": str(patient_id)}}

        if document_id is not None and document_type is not None:
            where = {
                "$and": [
                    {"patient_id": {"$eq": str(patient_id)}},
                    {"document_id": {"$eq": str(document_id)}},
                    {"document_type": {"$eq": str(document_type)}},
                ]
            }
        elif document_id is not None:
            where = {
                "$and": [
                    {"patient_id": {"$eq": str(patient_id)}},
                    {"document_id": {"$eq": str(document_id)}},
                ]
            }
        elif document_type is not None:
            where = {
                "$and": [
                    {"patient_id": {"$eq": str(patient_id)}},
                    {"document_type": {"$eq": str(document_type)}},
                ]
            }

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["metadatas", "distances", "documents"],
            )
        except Exception as exc:
            # Graceful degradation — log type only, not query content
            logger.error("Vector similarity search failed: %s", type(exc).__name__)
            return []

        search_results: list[VectorSearchResult] = []
        ids_list = results.get("ids", [[]])[0]
        metadatas_list = results.get("metadatas", [[]])[0]
        distances_list = results.get("distances", [[]])[0]

        for vec_id, meta, dist in zip(ids_list, metadatas_list, distances_list):
            search_results.append(
                VectorSearchResult(
                    chunk_id=vec_id,
                    document_id=meta.get("document_id", ""),
                    patient_id=meta.get("patient_id", ""),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    page_number=int(meta["page_number"]) if meta.get("page_number") is not None else None,
                    document_type=meta.get("document_type", ""),
                    distance=float(dist),
                    metadata=meta,
                )
            )

        return search_results

    # ------------------------------------------------------------------
    # Delete operations
    # ------------------------------------------------------------------

    def delete_by_document(self, document_id: str) -> int:
        """Remove all vectors for a given document_id.

        Returns:
            Number of vectors deleted.
        """
        try:
            existing = self._collection.get(
                where={"document_id": {"$eq": str(document_id)}},
                include=[],
            )
            ids_to_delete = existing.get("ids", [])
            if ids_to_delete:
                self._collection.delete(ids=ids_to_delete)
                logger.debug("Deleted %d vectors for document_id='%s'.", len(ids_to_delete), document_id)
            return len(ids_to_delete)
        except Exception as exc:
            logger.error("delete_by_document failed for document_id='%s': %s", document_id, type(exc).__name__)
            raise RuntimeError(f"Vector deletion failed for document '{document_id}': {exc}") from exc

    def delete_by_vector_ids(self, vector_ids: list[str]) -> int:
        """Remove vectors by their explicit IDs.

        Returns:
            Number of vectors requested for deletion.
        """
        if not vector_ids:
            return 0
        try:
            self._collection.delete(ids=vector_ids)
            logger.debug("Deleted %d vectors by explicit IDs.", len(vector_ids))
            return len(vector_ids)
        except Exception as exc:
            logger.error("delete_by_vector_ids failed: %s", type(exc).__name__)
            raise RuntimeError(f"Vector deletion by ID failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Utility operations
    # ------------------------------------------------------------------

    def count(self, patient_id: Optional[str] = None) -> int:
        """Count vectors in the collection.

        Args:
            patient_id: If provided, count only vectors for that patient.
        """
        if patient_id is not None:
            result = self._collection.get(
                where={"patient_id": {"$eq": str(patient_id)}},
                include=[],
            )
            return len(result.get("ids", []))
        return self._collection.count()

    def health_check(self) -> dict[str, Any]:
        """Verify ChromaDB collection is accessible.

        Returns a safe dict that does NOT include internal filesystem paths.
        """
        try:
            count = self._collection.count()
            return {
                "healthy": True,
                "collection_name": self._collection_name,
                "vector_count": count,
                "provider": "chromadb",
            }
        except Exception as exc:
            logger.warning("ChromaVectorStore health check failed: %s", type(exc).__name__)
            return {
                "healthy": False,
                "collection_name": self._collection_name,
                "provider": "chromadb",
                "error": type(exc).__name__,
            }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_vector_store(
    db_path: str,
    collection_name: str = "medical_documents",
) -> BaseVectorStore:
    """Instantiate the configured vector store.

    Only ChromaDB is supported in Phase 8.4.  Future backends (pgvector,
    OpenSearch, Bedrock) can be added here without modifying callers.
    """
    return ChromaVectorStore(db_path=db_path, collection_name=collection_name)

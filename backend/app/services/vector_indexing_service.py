"""
Vector indexing service for MediGen AI — Phase 8.4.

Responsibilities:
1. Read DocumentChunk records for a MedicalDocument.
2. Generate embeddings via BaseEmbeddingProvider.
3. Upsert vectors into ChromaVectorStore with patient-isolating metadata.
4. Persist returned vector IDs back to DocumentChunk.vector_id.
5. Remove stale vectors when a document is reprocessed or deleted.
6. Keep document processing_status consistent with indexing outcome.

Security:
- Chunk content and embeddings are NEVER written to logs.
- patient_id is included in every vector's metadata for isolation.
- Any failure stops the pipeline and marks the document as failed.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import BaseEmbeddingProvider
from app.ai.vector_store import BaseVectorStore
from app.models.document import DocumentChunk, MedicalDocument
from app.schemas.document import DocumentProcessingStatus

logger = logging.getLogger(__name__)


def build_vector_metadata(
    chunk: DocumentChunk,
    document: MedicalDocument,
) -> dict:
    """Build ChromaDB metadata dict for a single chunk.

    Includes the minimum fields required for patient-scoped retrieval.
    Never includes raw chunk content or embedding values.
    """
    return {
        "patient_id": str(document.patient_id),
        "document_id": document.document_id,
        "chunk_id": chunk.chunk_id,
        "chunk_index": chunk.chunk_index,
        "page_number": chunk.page_number if chunk.page_number is not None else -1,
        "document_type": document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type),
    }


def index_document_chunks(
    db: Session,
    document: MedicalDocument,
    embedding_provider: BaseEmbeddingProvider,
    vector_store: BaseVectorStore,
) -> MedicalDocument:
    """Generate embeddings and upsert all chunks for a document into the vector store.

    This function:
    1. Loads all DocumentChunk records for the document.
    2. Generates embeddings in batch.
    3. Upserts into vector store with full patient-isolating metadata.
    4. Writes vector IDs back to DocumentChunk.vector_id in the database.
    5. Updates document.processing_status = COMPLETED on success.
    6. Sets FAILED state on any error without losing chunk content.

    Args:
        db: Active SQLAlchemy session.
        document: MedicalDocument ORM instance (chunks must already exist).
        embedding_provider: Concrete BaseEmbeddingProvider instance.
        vector_store: Concrete BaseVectorStore instance.

    Returns:
        Updated MedicalDocument instance.
    """
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
    )

    if not chunks:
        logger.warning(
            "index_document_chunks: No chunks found for document id=%d. Marking failed.",
            document.id,
        )
        document.processing_status = DocumentProcessingStatus.FAILED
        document.error_message = "No chunks available for vector indexing."
        db.commit()
        db.refresh(document)
        return document

    try:
        # Generate embeddings — do NOT log text content
        texts = [chunk.content for chunk in chunks]
        embeddings = embedding_provider.embed_documents(texts)

        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedding provider returned {len(embeddings)} vectors for {len(chunks)} chunks."
            )

        # Build metadata and IDs — use chunk_id as the vector ID in ChromaDB
        vector_ids = [chunk.chunk_id for chunk in chunks]
        metadatas = [build_vector_metadata(chunk, document) for chunk in chunks]
        # Pass text to ChromaDB for reference (stored internally, not returned to API)
        documents_text = [chunk.content for chunk in chunks]

        # Upsert all vectors atomically
        vector_store.upsert(
            vector_ids=vector_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents_text,
        )

        # Persist vector IDs back to DocumentChunk records
        for chunk, vid in zip(chunks, vector_ids):
            chunk.vector_id = vid

        # Mark document as fully indexed
        document.processing_status = DocumentProcessingStatus.COMPLETED
        document.error_message = None
        document.total_chunks = len(chunks)

        db.commit()
        db.refresh(document)

        logger.info(
            "Indexed %d chunks for document id=%d [patient_id=%s].",
            len(chunks),
            document.id,
            document.patient_id,
        )
        return document

    except Exception as exc:
        db.rollback()
        logger.error(
            "Vector indexing failed for document id=%d: %s",
            document.id,
            type(exc).__name__,
        )
        # Record failure without exposing details that may contain medical content
        document.processing_status = DocumentProcessingStatus.FAILED
        document.error_message = f"Vector indexing failed: {type(exc).__name__}: {str(exc)[:300]}"
        db.commit()
        db.refresh(document)
        return document


def remove_document_vectors(
    document: MedicalDocument,
    vector_store: BaseVectorStore,
) -> int:
    """Remove all vectors for a document from the vector store.

    Safe to call even if no vectors exist for the document.

    Args:
        document: MedicalDocument to remove vectors for.
        vector_store: Active vector store instance.

    Returns:
        Number of vectors removed.
    """
    try:
        count = vector_store.delete_by_document(document_id=document.document_id)
        logger.debug(
            "Removed %d vectors for document id=%d from vector store.",
            count,
            document.id,
        )
        return count
    except Exception as exc:
        logger.error(
            "remove_document_vectors failed for document id=%d: %s",
            document.id,
            type(exc).__name__,
        )
        raise RuntimeError(
            f"Failed to remove vectors for document '{document.document_id}': {exc}"
        ) from exc

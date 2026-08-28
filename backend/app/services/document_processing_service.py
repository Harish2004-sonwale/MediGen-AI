"""
Document processing orchestration service for MediGen AI — Phase 8.3 + 8.4.

Processing pipeline:
    1. Mark document as PROCESSING.
    2. Extract text from the stored file (PDF/DOCX/TXT).
    3. Chunk the extracted text with semantic boundary preservation.
    4. Delete any existing chunks (for idempotent reprocessing).
    5. Remove stale vectors from ChromaDB (for idempotent reprocessing).
    6. Persist new DocumentChunk records.
    7. Generate embeddings for all chunks.
    8. Upsert vectors into ChromaDB with patient-isolating metadata.
    9. Save vector IDs back to DocumentChunk.vector_id.
   10. Mark document as COMPLETED.

On any failure the document is marked FAILED with a descriptive error.

Security:
- Chunk content and embeddings are NEVER written to logs.
- patient_id is enforced at the vector store layer.
"""

from datetime import datetime, timezone
import logging
import os
import secrets
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.chunker import chunk_extracted_document
from app.ai.embeddings import get_embedding_provider
from app.ai.extractors import extract_document_text
from app.ai.vector_store import get_vector_store
from app.core.config import settings
from app.models.document import DocumentChunk, MedicalDocument
from app.schemas.document import DocumentProcessingStatus
from app.services.vector_indexing_service import index_document_chunks, remove_document_vectors

logger = logging.getLogger(__name__)


def generate_unique_chunk_id(db: Session) -> str:
    """Generate unique public chunk identifier (e.g. CHK-20260828-A1B2)."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        random_suffix = secrets.token_hex(2).upper()
        candidate = f"CHK-{date_part}-{random_suffix}"
        exists = db.scalar(select(DocumentChunk.id).where(DocumentChunk.chunk_id == candidate))
        if not exists:
            return candidate
    return f"CHK-{date_part}-{secrets.token_hex(4).upper()}"


def process_medical_document(db: Session, document: MedicalDocument) -> MedicalDocument:
    """Execute the full document processing pipeline: extract → chunk → embed → index.

    This function is idempotent:
    - Existing chunks are deleted before new ones are created.
    - Existing vectors are removed from ChromaDB before new ones are upserted.
    - Repeated calls for the same document never produce duplicate records.

    Args:
        db: Active SQLAlchemy session.
        document: MedicalDocument instance to process.

    Returns:
        Updated MedicalDocument with processing_status COMPLETED or FAILED.
    """
    if not document.storage_path or not os.path.exists(document.storage_path):
        document.processing_status = DocumentProcessingStatus.FAILED
        document.error_message = "Physical document file not found on disk."
        db.commit()
        db.refresh(document)
        return document

    # Mark as processing
    document.processing_status = DocumentProcessingStatus.PROCESSING
    document.error_message = None
    db.commit()
    db.refresh(document)

    try:
        # ------------------------------------------------------------------
        # Phase 8.3: Text extraction and chunking
        # ------------------------------------------------------------------

        extracted = extract_document_text(
            file_path=document.storage_path,
            file_extension=document.file_extension,
        )

        chunks_data = chunk_extracted_document(
            extracted=extracted,
            chunk_size_tokens=settings.DOCUMENT_CHUNK_SIZE_TOKENS,
            chunk_overlap_tokens=settings.DOCUMENT_CHUNK_OVERLAP_TOKENS,
        )

        if not chunks_data:
            raise ValueError("Document contains no extractable clinical text.")

        # ------------------------------------------------------------------
        # Idempotency: remove existing vectors and chunks
        # ------------------------------------------------------------------

        # Remove stale vectors from ChromaDB first (safe if none exist)
        try:
            vector_store = get_vector_store(
                db_path=settings.VECTOR_DB_PATH,
                collection_name=settings.VECTOR_COLLECTION_NAME,
            )
            remove_document_vectors(document=document, vector_store=vector_store)
        except Exception as vec_exc:
            # Vector cleanup failure should not abort chunk processing
            logger.warning(
                "Pre-processing vector cleanup failed for document id=%d: %s. Continuing.",
                document.id,
                type(vec_exc).__name__,
            )

        # Remove stale chunks from database
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

        # ------------------------------------------------------------------
        # Insert new chunks
        # ------------------------------------------------------------------

        for chunk in chunks_data:
            chunk_orm = DocumentChunk(
                chunk_id=generate_unique_chunk_id(db),
                document_id=document.id,
                patient_id=document.patient_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                content=chunk.content,
                token_count=chunk.token_count,
                vector_id=None,
            )
            db.add(chunk_orm)

        # Update document page count before committing chunks
        document.page_count = extracted.page_count
        document.total_chunks = len(chunks_data)
        # Keep PROCESSING status until vector indexing completes
        document.processing_status = DocumentProcessingStatus.PROCESSING

        db.commit()
        db.refresh(document)

        # ------------------------------------------------------------------
        # Phase 8.4: Embedding generation and vector indexing
        # ------------------------------------------------------------------

        embedding_provider = get_embedding_provider(
            provider=settings.EMBEDDING_PROVIDER,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        vector_store = get_vector_store(
            db_path=settings.VECTOR_DB_PATH,
            collection_name=settings.VECTOR_COLLECTION_NAME,
        )

        document = index_document_chunks(
            db=db,
            document=document,
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        )

        return document

    except Exception as exc:
        db.rollback()
        logger.error(
            "process_medical_document failed for document id=%d: %s",
            document.id,
            type(exc).__name__,
        )
        document.processing_status = DocumentProcessingStatus.FAILED
        document.error_message = str(exc)[:500]
        document.total_chunks = 0
        db.commit()
        db.refresh(document)
        return document

"""
Clinical RAG Service for MediGen AI.

Phase 8.5: Clinical RAG Query, Context Retrieval & Grounded Synthesis.

Responsibilities:
1. Patient resolution and RBAC validation.
2. Generating query embeddings using BaseEmbeddingProvider.
3. Patient-scoped similarity search against ChromaVectorStore.
4. Authoritative SQL verification of retrieved chunks (cross-patient isolation).
5. Grounded context construction.
6. LLM synthesis via BaseLLMProvider.
7. Strict citation validation and deduplication.
8. Zero-PHI operational logging.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.context_builder import (
    INSUFFICIENT_INFORMATION_MESSAGE,
    GroundedContextChunk,
)
from app.ai.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.ai.llm import BaseLLMProvider, CitationData, get_llm_provider
from app.ai.vector_store import BaseVectorStore, get_vector_store
from app.core.config import settings
from app.models.document import DocumentChunk, MedicalDocument
from app.models.patient import Patient
from app.models.user import User
from app.schemas.rag import RAGCitation, RAGQueryRequest, RAGQueryResponse
from app.schemas.user import UserRole
from app.services.appointment_service import resolve_patient
from app.services.document_service import has_patient_clinical_access

logger = logging.getLogger(__name__)


def validate_patient_rag_access(db: Session, current_user: User, patient: Patient) -> None:
    """Validate that the authenticated user has permission to query this patient's records.

    Raises:
        PermissionError: If user lacks authorized clinical access.
    """
    if current_user.role in (UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        return

    if current_user.role == UserRole.PATIENT:
        if not patient.email or patient.email.strip().lower() != current_user.email.strip().lower():
            logger.warning(
                "Patient user %s attempted unauthorized RAG query on patient %s",
                current_user.id,
                patient.patient_id,
            )
            raise PermissionError("You are only permitted to query your own medical records.")
        return

    if current_user.role == UserRole.DOCTOR:
        if not has_patient_clinical_access(db, current_user, patient):
            logger.warning(
                "Doctor user %s attempted unauthorized RAG query on unlinked patient %s",
                current_user.id,
                patient.patient_id,
            )
            raise PermissionError(
                "You do not have an active clinical relationship with this patient."
            )
        return

    raise PermissionError("Operation not permitted for current user role.")


def execute_rag_query(
    db: Session,
    request: RAGQueryRequest,
    current_user: User,
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    vector_store: Optional[BaseVectorStore] = None,
    llm_provider: Optional[BaseLLMProvider] = None,
    chat_history: Optional[list[dict[str, str]]] = None,
) -> RAGQueryResponse:
    """Execute a grounded clinical RAG inquiry against an authorized patient's records.

    Pipeline:
    1. Resolve patient and enforce strict RBAC.
    2. Generate query embedding.
    3. Perform patient-scoped vector similarity search.
    4. Apply confidence/relevance filtering (RAG_MIN_SIMILARITY).
    5. Validate and load authoritative DocumentChunk rows from PostgreSQL.
    6. Construct grounded context.
    7. Synthesize grounded answer via BaseLLMProvider (with multi-turn history if present).
    8. Validate and deduplicate citations against retrieved chunks.
    9. Return RAGQueryResponse without leaking PHI or filesystem paths.
    """
    start_time = time.perf_counter()

    # Step 1: Resolve target patient
    patient = resolve_patient(db, request.patient_id)
    if not patient:
        raise KeyError(f"Patient '{request.patient_id}' not found.")

    # Step 2: Enforce RBAC & isolation
    validate_patient_rag_access(db, current_user, patient)

    # Step 3: Instantiate providers
    emb_provider = embedding_provider or get_embedding_provider(
        provider=settings.EMBEDDING_PROVIDER,
        dimension=settings.EMBEDDING_DIMENSION,
    )
    v_store = vector_store or get_vector_store(
        db_path=settings.VECTOR_DB_PATH,
        collection_name=settings.VECTOR_COLLECTION_NAME,
    )
    llm = llm_provider or get_llm_provider(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
    )

    # Step 4: Generate query embedding
    clean_query = request.query.strip()
    query_embedding = emb_provider.embed_query(clean_query)

    # Step 5: Patient-scoped vector retrieval
    top_k = min(request.top_k or settings.RAG_TOP_K, settings.RAG_MAX_CONTEXT_CHUNKS)
    raw_vector_results = v_store.similarity_search(
        query_embedding=query_embedding,
        patient_id=str(patient.id),
        top_k=top_k,
    )

    # Step 5b: Filter by min_similarity threshold
    min_sim = request.min_similarity if request.min_similarity is not None else settings.RAG_MIN_SIMILARITY
    if min_sim > 0.0:
        filtered_vector_results = [
            r for r in raw_vector_results
            if (1.0 - r.distance) >= min_sim
        ]
    else:
        filtered_vector_results = raw_vector_results

    if not filtered_vector_results:
        logger.info(
            "RAG query returned 0 vector results above similarity threshold (min_sim=%.2f) for patient %s",
            min_sim,
            patient.patient_id,
        )
        return RAGQueryResponse(
            answer=INSUFFICIENT_INFORMATION_MESSAGE,
            citations=[],
            insufficient_information=True,
            retrieved_chunks=0,
            patient_id=patient.patient_id,
        )

    # Step 6: Authoritative SQL mapping & patient ownership verification
    retrieved_chunk_ids = [r.chunk_id for r in filtered_vector_results]
    distance_map = {r.chunk_id: r.distance for r in filtered_vector_results}

    # Query matching chunks and verify patient ownership at database level
    stmt = (
        select(DocumentChunk, MedicalDocument)
        .join(MedicalDocument, DocumentChunk.document_id == MedicalDocument.id)
        .where(
            DocumentChunk.chunk_id.in_(retrieved_chunk_ids),
            DocumentChunk.patient_id == patient.id,
            MedicalDocument.patient_id == patient.id,
        )
    )
    db_rows = db.execute(stmt).all()

    # Build validated GroundedContextChunk list in retrieved rank order
    chunk_map = {chunk.chunk_id: (chunk, doc) for chunk, doc in db_rows}
    context_chunks: list[GroundedContextChunk] = []

    for cid in retrieved_chunk_ids:
        if cid in chunk_map:
            chunk, doc = chunk_map[cid]
            context_chunks.append(
                GroundedContextChunk(
                    document_id=doc.document_id,
                    title=doc.title,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                    document_type=doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type),
                    content=chunk.content,
                    distance=distance_map.get(cid, 0.0),
                )
            )

    if not context_chunks:
        logger.info(
            "RAG query: all vector results failed SQL validation for patient %s",
            patient.patient_id,
        )
        return RAGQueryResponse(
            answer=INSUFFICIENT_INFORMATION_MESSAGE,
            citations=[],
            insufficient_information=True,
            retrieved_chunks=0,
            patient_id=patient.patient_id,
        )

    # Step 7: LLM Grounded Synthesis
    llm_response = llm.generate_grounded_response(
        query=clean_query,
        context_chunks=context_chunks,
        chat_history=chat_history,
    )

    # Step 8: Validate and deduplicate citations against authorized context chunks
    authorized_chunk_ids = {c.chunk_id: c for c in context_chunks}
    validated_citations: list[RAGCitation] = []
    seen_citation_chunks: set[str] = set()

    for cit in llm_response.citations:
        cid = cit.chunk_id if isinstance(cit, CitationData) else cit.get("chunk_id")
        if cid and cid in authorized_chunk_ids and cid not in seen_citation_chunks:
            source_chunk = authorized_chunk_ids[cid]
            validated_citations.append(
                RAGCitation(
                    document_id=source_chunk.document_id,
                    title=source_chunk.title,
                    page_number=source_chunk.page_number,
                    chunk_id=source_chunk.chunk_id,
                    document_type=source_chunk.document_type,
                )
            )
            seen_citation_chunks.add(cid)

    # If insufficient information, enforce empty citations
    if llm_response.insufficient_information:
        validated_citations = []
        answer = INSUFFICIENT_INFORMATION_MESSAGE
    else:
        answer = llm_response.answer

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "RAG query completed for patient %s in %.2fms [retrieved=%d, citations=%d, insufficient=%s]",
        patient.patient_id,
        elapsed_ms,
        len(context_chunks),
        len(validated_citations),
        llm_response.insufficient_information,
    )

    return RAGQueryResponse(
        answer=answer,
        citations=validated_citations,
        insufficient_information=llm_response.insufficient_information,
        retrieved_chunks=len(context_chunks),
        patient_id=patient.patient_id,
    )

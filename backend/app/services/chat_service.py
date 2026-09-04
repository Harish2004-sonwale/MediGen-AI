"""Clinical Chat and Session Persistence Service.

Phase 8.6: Multi-turn clinical chat/session memory, persistence & patient isolation.

Responsibilities:
1. Patient-scoped session lifecycle management (create, list, get history, close).
2. Authoritative PostgreSQL persistence of sessions and messages.
3. Multi-turn conversation memory within patient boundaries.
4. Grounded RAG synthesis with relevance/similarity filtering.
5. Strict RBAC validation, citation verification, prompt injection defense, and zero-PHI logging.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.embeddings import BaseEmbeddingProvider
from app.ai.llm import BaseLLMProvider
from app.ai.vector_store import BaseVectorStore
from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.models.patient import Patient
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.schemas.rag import RAGCitation, RAGQueryRequest
from app.services.appointment_service import resolve_patient
from app.services.rag_service import execute_rag_query, validate_patient_rag_access

logger = logging.getLogger(__name__)


def _generate_session_id() -> str:
    """Generate unique public session identifier (e.g. SES-20260828-A1B2C3D4)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:8].upper()
    return f"SES-{date_str}-{suffix}"


def _generate_message_id() -> str:
    """Generate unique public message identifier (e.g. MSG-20260828-A1B2C3D4)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:8].upper()
    return f"MSG-{date_str}-{suffix}"


def resolve_chat_session(db: Session, identifier: str | int) -> Optional[ChatSession]:
    """Look up a chat session by public session_id or database primary key ID."""
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        session = db.get(ChatSession, int(identifier))
        if session:
            return session
    stmt = select(ChatSession).where(ChatSession.session_id == str(identifier))
    return db.execute(stmt).scalar_one_or_none()


def create_chat_session(
    db: Session,
    request: ChatSessionCreate,
    current_user: User,
) -> ChatSessionResponse:
    """Create a new clinical consultation chat session for an authorized patient."""
    patient = resolve_patient(db, request.patient_id)
    if not patient:
        raise KeyError(f"Patient '{request.patient_id}' not found.")

    validate_patient_rag_access(db, current_user, patient)

    session_id = _generate_session_id()
    title = (request.title or "Clinical Consultation").strip()

    chat_session = ChatSession(
        session_id=session_id,
        patient_id=patient.id,
        user_id=current_user.id,
        title=title,
        is_active=True,
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    logger.info(
        "Created chat session %s for patient %s by user %s",
        chat_session.session_id,
        patient.patient_id,
        current_user.id,
    )

    return ChatSessionResponse(
        session_id=chat_session.session_id,
        patient_id=patient.patient_id,
        title=chat_session.title,
        is_active=chat_session.is_active,
        message_count=0,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def get_chat_session(
    db: Session,
    session_id: str,
    current_user: User,
) -> ChatSessionDetailResponse:
    """Retrieve full consultation session details and message history."""
    chat_session = resolve_chat_session(db, session_id)
    if not chat_session:
        raise KeyError(f"Chat session '{session_id}' not found.")

    patient = chat_session.patient
    validate_patient_rag_access(db, current_user, patient)

    formatted_messages = []
    for msg in chat_session.messages:
        citations = []
        if msg.citations:
            for c in msg.citations:
                citations.append(
                    RAGCitation(
                        document_id=c.get("document_id", ""),
                        title=c.get("title", ""),
                        page_number=c.get("page_number"),
                        chunk_id=c.get("chunk_id", ""),
                        document_type=c.get("document_type"),
                    )
                )

        formatted_messages.append(
            ChatMessageResponse(
                message_id=msg.message_id,
                session_id=chat_session.session_id,
                sender_role=msg.sender_role,
                content=msg.content,
                citations=citations,
                insufficient_information=msg.insufficient_information,
                retrieved_chunks=msg.retrieved_chunks,
                created_at=msg.created_at,
            )
        )

    return ChatSessionDetailResponse(
        session_id=chat_session.session_id,
        patient_id=patient.patient_id,
        title=chat_session.title,
        is_active=chat_session.is_active,
        messages=formatted_messages,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def list_patient_chat_sessions(
    db: Session,
    patient_id: str,
    current_user: User,
    is_active: Optional[bool] = None,
) -> ChatSessionListResponse:
    """List all clinical consultation sessions for a patient."""
    patient = resolve_patient(db, patient_id)
    if not patient:
        raise KeyError(f"Patient '{patient_id}' not found.")

    validate_patient_rag_access(db, current_user, patient)

    query = select(ChatSession).where(ChatSession.patient_id == patient.id)
    if is_active is not None:
        query = query.where(ChatSession.is_active == is_active)

    query = query.order_by(ChatSession.created_at.desc())
    sessions = db.execute(query).scalars().all()

    session_responses = []
    for s in sessions:
        msg_count = db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == s.id)
        ).scalar_one() or 0

        session_responses.append(
            ChatSessionResponse(
                session_id=s.session_id,
                patient_id=patient.patient_id,
                title=s.title,
                is_active=s.is_active,
                message_count=msg_count,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )

    return ChatSessionListResponse(
        total=len(session_responses),
        sessions=session_responses,
    )


def close_chat_session(
    db: Session,
    session_id: str,
    current_user: User,
) -> ChatSessionResponse:
    """Close an active clinical consultation session."""
    chat_session = resolve_chat_session(db, session_id)
    if not chat_session:
        raise KeyError(f"Chat session '{session_id}' not found.")

    patient = chat_session.patient
    validate_patient_rag_access(db, current_user, patient)

    chat_session.is_active = False
    db.commit()
    db.refresh(chat_session)

    msg_count = db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == chat_session.id)
    ).scalar_one() or 0

    logger.info("Closed chat session %s for patient %s", chat_session.session_id, patient.patient_id)

    return ChatSessionResponse(
        session_id=chat_session.session_id,
        patient_id=patient.patient_id,
        title=chat_session.title,
        is_active=chat_session.is_active,
        message_count=msg_count,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def send_chat_message(
    db: Session,
    session_id: str,
    request: ChatMessageCreate,
    current_user: User,
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    vector_store: Optional[BaseVectorStore] = None,
    llm_provider: Optional[BaseLLMProvider] = None,
) -> ChatMessageResponse:
    """Submit a user inquiry to a session and generate a grounded assistant response.

    Pipeline:
    1. Resolve session and enforce active status + RBAC.
    2. Save user message turn in PostgreSQL.
    3. Retrieve recent session turns for multi-turn history.
    4. Execute grounded RAG synthesis scoped to session patient.
    5. Save assistant message turn with structured citations in PostgreSQL.
    6. Update session timestamp and commit transaction.
    """
    chat_session = resolve_chat_session(db, session_id)
    if not chat_session:
        raise KeyError(f"Chat session '{session_id}' not found.")

    if not chat_session.is_active:
        raise ValueError("Cannot send a message to an inactive or closed consultation session.")

    patient = chat_session.patient
    validate_patient_rag_access(db, current_user, patient)

    clean_content = request.message.strip()

    # 1. Record user turn
    user_msg_id = _generate_message_id()
    user_msg = ChatMessage(
        message_id=user_msg_id,
        session_id=chat_session.id,
        sender_role="user",
        content=clean_content,
        citations=None,
        insufficient_information=False,
        retrieved_chunks=0,
    )
    db.add(user_msg)
    db.flush()

    # 2. Build multi-turn history
    recent_history_limit = settings.CHAT_HISTORY_MAX_TURNS * 2
    past_messages = (
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat_session.id, ChatMessage.id < user_msg.id)
            .order_by(ChatMessage.id.desc())
            .limit(recent_history_limit)
        )
        .scalars()
        .all()
    )
    # Reverse to chronological order
    chronological_history = list(reversed(past_messages))
    formatted_history = [
        {"role": m.sender_role, "content": m.content}
        for m in chronological_history
    ]

    # 3. Execute grounded RAG synthesis with patient isolation & history
    rag_request = RAGQueryRequest(
        patient_id=patient.patient_id,
        query=clean_content,
        top_k=request.top_k or settings.RAG_TOP_K,
        min_similarity=request.min_similarity,
    )

    rag_response = execute_rag_query(
        db=db,
        request=rag_request,
        current_user=current_user,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
        chat_history=formatted_history,
    )

    # 4. Record assistant turn
    citations_data = [cit.model_dump() for cit in rag_response.citations]
    assistant_msg_id = _generate_message_id()
    assistant_msg = ChatMessage(
        message_id=assistant_msg_id,
        session_id=chat_session.id,
        sender_role="assistant",
        content=rag_response.answer,
        citations=citations_data if citations_data else None,
        insufficient_information=rag_response.insufficient_information,
        retrieved_chunks=rag_response.retrieved_chunks,
    )
    db.add(assistant_msg)

    # 5. Update session timestamp
    chat_session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

    logger.info(
        "Chat message completed for session %s (patient %s) [citations=%d, insufficient=%s]",
        chat_session.session_id,
        patient.patient_id,
        len(rag_response.citations),
        rag_response.insufficient_information,
    )

    return ChatMessageResponse(
        message_id=assistant_msg.message_id,
        session_id=chat_session.session_id,
        sender_role="assistant",
        content=assistant_msg.content,
        citations=rag_response.citations,
        insufficient_information=assistant_msg.insufficient_information,
        retrieved_chunks=assistant_msg.retrieved_chunks,
        created_at=assistant_msg.created_at,
    )


def stream_chat_message(
    db: Session,
    session_id: str,
    request: ChatMessageCreate,
    current_user: User,
    embedding_provider: Optional[BaseEmbeddingProvider] = None,
    vector_store: Optional[BaseVectorStore] = None,
    llm_provider: Optional[BaseLLMProvider] = None,
):
    """Stream assistant response tokens via Server-Sent Events (SSE).

    SSE Protocol Events:
    - event: start -> {"session_id": "...", "message_id": "..."}
    - event: delta -> {"text": "..."}
    - event: citation -> {"document_id": "...", "title": "...", "chunk_id": "..."}
    - event: done -> {"message_id": "...", "completed": true, "insufficient_information": bool, "retrieved_chunks": int}
    - event: error -> {"error": "..."}
    """
    import json
    from app.ai.context_builder import (
        INSUFFICIENT_INFORMATION_MESSAGE,
        GroundedContextChunk,
    )
    from app.ai.embeddings import get_embedding_provider
    from app.ai.llm import CitationData, get_llm_provider
    from app.ai.vector_store import get_vector_store
    from app.models.document import DocumentChunk, MedicalDocument

    # 1. Resolve session & RBAC
    chat_session = resolve_chat_session(db, session_id)
    if not chat_session:
        yield f"event: error\ndata: {json.dumps({'error': f'Chat session {session_id} not found.'})}\n\n"
        return

    if not chat_session.is_active:
        yield f"event: error\ndata: {json.dumps({'error': 'Cannot send a message to an inactive consultation session.'})}\n\n"
        return

    patient = chat_session.patient
    try:
        validate_patient_rag_access(db, current_user, patient)
    except Exception as exc:
        yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        return

    clean_content = request.message.strip()
    if not clean_content:
        yield f"event: error\ndata: {json.dumps({'error': 'Message cannot be empty.'})}\n\n"
        return

    try:
        # 2. Persist user message turn
        user_msg_id = _generate_message_id()
        user_msg = ChatMessage(
            message_id=user_msg_id,
            session_id=chat_session.id,
            sender_role="user",
            content=clean_content,
            citations=None,
            insufficient_information=False,
            retrieved_chunks=0,
        )
        db.add(user_msg)
        db.commit()

        # 3. Retrieve prior chat history
        recent_history_limit = settings.CHAT_HISTORY_MAX_TURNS * 2
        past_messages = (
            db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == chat_session.id, ChatMessage.id < user_msg.id)
                .order_by(ChatMessage.id.desc())
                .limit(recent_history_limit)
            )
            .scalars()
            .all()
        )
        chronological_history = list(reversed(past_messages))
        formatted_history = [
            {"role": m.sender_role, "content": m.content}
            for m in chronological_history
        ]

        # 4. Resolve providers using existing application configuration
        emb_prov = embedding_provider or get_embedding_provider(
            provider=settings.EMBEDDING_PROVIDER,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        v_store = vector_store or get_vector_store(
            db_path=settings.VECTOR_DB_PATH,
            collection_name=settings.VECTOR_COLLECTION_NAME,
        )
        l_prov = llm_provider or get_llm_provider(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
        )

        # 5. Execute vector search with patient isolation
        query_emb = emb_prov.embed_query(clean_content)
        top_k = request.top_k or settings.RAG_TOP_K
        search_results = v_store.similarity_search(
            query_embedding=query_emb,
            patient_id=str(patient.id),
            top_k=top_k,
        )

        # Apply min_similarity filter if configured
        min_sim = request.min_similarity if request.min_similarity is not None else settings.RAG_MIN_SIMILARITY
        if min_sim > 0.0:
            search_results = [r for r in search_results if r.similarity >= min_sim]

        # 6. Authoritative PostgreSQL chunk verification
        retrieved_cids = [r.chunk_id for r in search_results]
        grounded_chunks: list[GroundedContextChunk] = []

        if retrieved_cids:
            stmt = (
                select(DocumentChunk, MedicalDocument)
                .join(MedicalDocument, DocumentChunk.document_id == MedicalDocument.id)
                .where(
                    DocumentChunk.chunk_id.in_(retrieved_cids),
                    MedicalDocument.patient_id == patient.id,
                )
            )
            rows = db.execute(stmt).all()
            chunk_doc_map = {chunk.chunk_id: (chunk, doc) for chunk, doc in rows}

            for r in search_results:
                if r.chunk_id in chunk_doc_map:
                    chunk, doc = chunk_doc_map[r.chunk_id]
                    grounded_chunks.append(
                        GroundedContextChunk(
                            chunk_id=chunk.chunk_id,
                            document_id=doc.document_id,
                            title=doc.title,
                            content=chunk.content,
                            page_number=chunk.page_number,
                            document_type=doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type),
                            distance=r.distance,
                        )
                    )

        assistant_msg_id = _generate_message_id()
        yield f"event: start\ndata: {json.dumps({'session_id': chat_session.session_id, 'message_id': assistant_msg_id})}\n\n"

        # 7. Handle insufficient context or stream tokens
        accumulated_tokens: list[str] = []
        if not grounded_chunks:
            yield f"event: delta\ndata: {json.dumps({'text': INSUFFICIENT_INFORMATION_MESSAGE})}\n\n"
            full_answer = INSUFFICIENT_INFORMATION_MESSAGE
            insufficient = True
            citations_list: list[dict] = []
        else:
            stream_gen = l_prov.generate_grounded_response_stream(
                query=clean_content,
                context_chunks=grounded_chunks,
                chat_history=formatted_history,
            )
            for delta in stream_gen:
                accumulated_tokens.append(delta)
                yield f"event: delta\ndata: {json.dumps({'text': delta})}\n\n"

            full_answer = "".join(accumulated_tokens).strip()
            insufficient = INSUFFICIENT_INFORMATION_MESSAGE.lower() in full_answer.lower()

            # Build citations
            citations_list = []
            if not insufficient:
                seen_cids = set()
                for c in grounded_chunks:
                    if c.chunk_id not in seen_cids:
                        cit_dict = {
                            "document_id": c.document_id,
                            "title": c.title,
                            "page_number": c.page_number,
                            "chunk_id": c.chunk_id,
                            "document_type": c.document_type,
                        }
                        citations_list.append(cit_dict)
                        seen_cids.add(c.chunk_id)
                        yield f"event: citation\ndata: {json.dumps(cit_dict)}\n\n"

        # 8. Persist assistant message in PostgreSQL
        assistant_msg = ChatMessage(
            message_id=assistant_msg_id,
            session_id=chat_session.id,
            sender_role="assistant",
            content=full_answer,
            citations=citations_list if citations_list else None,
            insufficient_information=insufficient,
            retrieved_chunks=len(grounded_chunks),
        )
        db.add(assistant_msg)
        chat_session.updated_at = datetime.now(timezone.utc)
        db.commit()

        # 9. Send final completion event
        yield f"event: done\ndata: {json.dumps({'message_id': assistant_msg_id, 'completed': True, 'insufficient_information': insufficient, 'retrieved_chunks': len(grounded_chunks)})}\n\n"

    except Exception as exc:
        db.rollback()
        logger.error("Error in streaming chat message: %s", type(exc).__name__)
        yield f"event: error\ndata: {json.dumps({'error': f'Streaming error: {str(exc)}'})}\n\n"

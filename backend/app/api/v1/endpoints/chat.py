"""Clinical Chat and Multi-Turn Consultation Endpoints.

Phase 8.6: Multi-turn clinical chat/session memory, persistence & isolation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.chat_service import (
    close_chat_session,
    create_chat_session,
    get_chat_session,
    list_patient_chat_sessions,
    resolve_chat_session,
    send_chat_message,
    stream_chat_message,
)
from app.services.rag_service import validate_patient_rag_access

router = APIRouter(prefix="/chat", tags=["Clinical Chat"])


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new clinical consultation chat session",
)
def create_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatSessionResponse:
    """Initiate a new patient-scoped clinical consultation session."""
    try:
        return create_chat_session(db=db, request=request, current_user=current_user)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical consultation sessions for a patient",
)
def list_sessions(
    patient_id: str = Query(..., description="Target patient identifier"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatSessionListResponse:
    """Retrieve all consultation sessions for an authorized patient."""
    try:
        return list_patient_chat_sessions(
            db=db,
            patient_id=patient_id,
            current_user=current_user,
            is_active=is_active,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full details and message history for a consultation session",
)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatSessionDetailResponse:
    """Retrieve full consultation session conversation history."""
    try:
        return get_chat_session(
            db=db,
            session_id=session_id,
            current_user=current_user,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Post a message inquiry and receive a grounded clinical response",
)
def post_message(
    session_id: str,
    request: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatMessageResponse:
    """Send a clinical query turn to an active consultation session.

    - Inquiries are grounded strictly against the session patient's authorized records.
    - Previous message history in the session provides multi-turn clinical context.
    - Validated citations are recorded and returned with the assistant turn.
    """
    try:
        return send_chat_message(
            db=db,
            session_id=session_id,
            request=request,
            current_user=current_user,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/sessions/{session_id}/messages/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream grounded clinical consultation response via SSE",
)
def post_message_stream(
    session_id: str,
    request: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream a clinical query turn to an active consultation session via Server-Sent Events (SSE).

    - Tokens/deltas are streamed in real time via SSE events (`start`, `delta`, `citation`, `done`).
    - Grounded citations and final message turns are persisted in PostgreSQL.
    """
    chat_session = resolve_chat_session(db, session_id)
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found.",
        )
    if not chat_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a message to an inactive or closed consultation session.",
        )
    try:
        validate_patient_rag_access(db, current_user, chat_session.patient)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        stream_chat_message(
            db=db,
            session_id=session_id,
            request=request,
            current_user=current_user,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Close an active clinical consultation session",
)
def close_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatSessionResponse:
    """Close and archive an active consultation session."""
    try:
        return close_chat_session(
            db=db,
            session_id=session_id,
            current_user=current_user,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

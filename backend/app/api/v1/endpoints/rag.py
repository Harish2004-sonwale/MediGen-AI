"""
Clinical RAG Query API Endpoints.

Phase 8.5: Clinical RAG Query, Context Retrieval & Grounded Synthesis.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import execute_rag_query

router = APIRouter(tags=["Clinical RAG"])


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query patient medical records with grounded RAG synthesis",
)
def query_patient_records(
    request: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RAGQueryResponse:
    """Execute a grounded clinical query across authorized patient medical documents.

    - Authenticated patients can query only their own records.
    - Authorized doctors can query only patients under their care.
    - Administrators and healthcare staff can query any patient.
    - Strict patient isolation is enforced at the database and vector store layer.
    """
    try:
        return execute_rag_query(
            db=db,
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

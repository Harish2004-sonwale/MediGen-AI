"""
Pydantic Schemas for Clinical RAG Query and Response.

Phase 8.5: Clinical RAG Query, Context Retrieval & Grounded Synthesis.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RAGCitation(BaseModel):
    """Structured citation referencing an authoritative source chunk."""

    document_id: str = Field(..., description="Public document ID (e.g. DOCU-20260828-A1B2)")
    title: str = Field(..., description="Document title")
    page_number: Optional[int] = Field(None, description="Source page number, if applicable")
    chunk_id: str = Field(..., description="Public chunk ID (e.g. CHK-20260828-C3D4)")
    document_type: Optional[str] = Field(None, description="Clinical document classification")

    model_config = ConfigDict(from_attributes=True)


class RAGQueryRequest(BaseModel):
    """Request payload for querying a patient's medical records via RAG."""

    patient_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Target patient identifier (public patient_id or database ID)",
        examples=["PAT-20260828-A1B2"],
    )
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Clinical question regarding the patient's records",
        examples=["What medications were prescribed during the patient's recent visit?"],
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of relevant context chunks to retrieve (1-20)",
    )
    min_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum similarity score threshold (0.0 to 1.0)",
    )


class RAGQueryResponse(BaseModel):
    """Grounded clinical RAG query response with structured citations."""

    answer: str = Field(..., description="Synthesized grounded clinical answer")
    citations: list[RAGCitation] = Field(
        default_factory=list,
        description="Structured citations linking facts to authoritative source chunks",
    )
    insufficient_information: bool = Field(
        ...,
        description="Flag indicating if the documents lacked sufficient information to answer",
    )
    retrieved_chunks: int = Field(
        ...,
        ge=0,
        description="Number of authorized chunks retrieved and evaluated",
    )
    patient_id: str = Field(..., description="Public identifier of the queried patient")

    model_config = ConfigDict(from_attributes=True)

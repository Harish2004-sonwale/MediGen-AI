"""Pydantic schemas for multi-turn clinical chat sessions and messages.

Phase 8.6: Multi-turn clinical chat/session memory, persistence & isolation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import RAGCitation


class ChatMessageCreate(BaseModel):
    """Payload for submitting a user inquiry within an existing chat session."""

    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
        description="Clinical query or follow-up question for the patient consultation",
        examples=["What medications was the patient prescribed for hypertension?"],
    )
    top_k: Optional[int] = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of context chunks to retrieve for this turn",
    )
    min_similarity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum vector similarity score threshold (0.0 - 1.0)",
    )


class ChatMessageResponse(BaseModel):
    """Schema representing an individual message turn in a consultation session."""

    message_id: str = Field(..., description="Unique message identifier (e.g. MSG-20260828-A1B2)")
    session_id: str = Field(..., description="Parent session identifier")
    sender_role: str = Field(..., description="Message author role: 'user' or 'assistant'")
    content: str = Field(..., description="Text content of the message turn")
    citations: list[RAGCitation] = Field(
        default_factory=list,
        description="Structured citations linking facts to authoritative source chunks",
    )
    insufficient_information: bool = Field(
        default=False,
        description="Flag indicating if the patient documents lacked sufficient context",
    )
    retrieved_chunks: int = Field(
        default=0,
        description="Number of authorized chunks retrieved and evaluated for this turn",
    )
    created_at: datetime = Field(..., description="Timestamp when message was recorded")

    model_config = ConfigDict(from_attributes=True)


class ChatSessionCreate(BaseModel):
    """Payload to initiate a new patient-scoped clinical consultation session."""

    patient_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Target patient identifier (public patient_id or database ID)",
        examples=["PAT-20260828-A1B2"],
    )
    title: Optional[str] = Field(
        default="Clinical Consultation",
        max_length=255,
        description="Optional descriptive title for the consultation session",
    )


class ChatSessionResponse(BaseModel):
    """Summary schema for a clinical consultation session."""

    session_id: str = Field(..., description="Unique session identifier (e.g. SES-20260828-A1B2)")
    patient_id: str = Field(..., description="Target patient public identifier")
    title: str = Field(..., description="Consultation session title")
    is_active: bool = Field(..., description="Whether the session is open for active inquiries")
    message_count: int = Field(default=0, description="Total number of message turns in session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session last updated timestamp")

    model_config = ConfigDict(from_attributes=True)


class ChatSessionDetailResponse(BaseModel):
    """Detailed schema for a clinical consultation session including message history."""

    session_id: str = Field(..., description="Unique session identifier")
    patient_id: str = Field(..., description="Target patient public identifier")
    title: str = Field(..., description="Consultation session title")
    is_active: bool = Field(..., description="Whether the session is open for active inquiries")
    messages: list[ChatMessageResponse] = Field(
        default_factory=list,
        description="Chronological list of conversation message turns",
    )
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session last updated timestamp")

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """Paginated or listed response containing multiple chat sessions."""

    total: int = Field(..., description="Total number of matching consultation sessions")
    sessions: list[ChatSessionResponse] = Field(
        default_factory=list,
        description="List of clinical consultation sessions",
    )

    model_config = ConfigDict(from_attributes=True)

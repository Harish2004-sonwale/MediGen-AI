"""Schemas for Longitudinal Clinical Timeline.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.rag import RAGCitation


class TimelineEventType(str, Enum):
    """Types of longitudinal patient timeline events."""

    ENCOUNTER = "encounter"
    APPOINTMENT = "appointment"
    DOCUMENT_UPLOAD = "document_upload"
    DIAGNOSIS = "diagnosis"
    MEDICATION_PRESCRIBED = "medication_prescribed"
    LAB_RESULT = "lab_result"
    PROCEDURE = "procedure"
    CLINICAL_EVENT = "clinical_event"


class ClinicalTimelineEvent(BaseModel):
    """Structured representation of a single historical clinical event."""

    event_id: str = Field(..., description="Unique event identifier (e.g. EVT-20260828-A1B2)")
    patient_id: str = Field(..., description="Target patient public identifier")
    event_date: datetime = Field(..., description="Timestamp when the clinical event occurred")
    event_type: TimelineEventType = Field(..., description="Category of the event")
    title: str = Field(..., description="Concise human-readable title")
    description: str = Field(..., description="Detailed description of the clinical event")
    source_document_id: Optional[str] = Field(None, description="Source document public identifier if applicable")
    source_chunk_id: Optional[str] = Field(None, description="Source text chunk ID if derived from extracted text")
    page_number: Optional[int] = Field(None, description="Page number within source document")
    confidence: Optional[float] = Field(1.0, description="Extraction certainty score (0.0 - 1.0)")
    citations: list[RAGCitation] = Field(default_factory=list, description="Authoritative grounding citations")

    model_config = ConfigDict(from_attributes=True)


class TimelineListResponse(BaseModel):
    """Paginated list of chronological timeline events."""

    total: int = Field(..., description="Total matching event count")
    patient_id: str = Field(..., description="Target patient identifier")
    events: list[ClinicalTimelineEvent] = Field(..., description="Chronological timeline events")


class TimelineSummaryResponse(BaseModel):
    """Grounded longitudinal patient history summary synthesized via RAG."""

    patient_id: str = Field(..., description="Target patient identifier")
    summary: str = Field(..., description="Clinically grounded narrative summary across history")
    citations: list[RAGCitation] = Field(default_factory=list, description="Grounding source citations")
    event_count: int = Field(..., description="Number of historical events evaluated")
    generated_at: datetime = Field(..., description="Generation timestamp")

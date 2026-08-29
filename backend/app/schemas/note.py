"""Pydantic schemas for Clinical Notes, AI Scribe Synthesis & Structured Documentation.

Phase 9.0.8: Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class NoteType(str, Enum):
    """Supported standardized clinical note types."""

    SOAP = "soap"
    CONSULTATION = "consultation"
    DISCHARGE_SUMMARY = "discharge_summary"
    PROCEDURE_NOTE = "procedure_note"
    REFERRAL_LETTER = "referral_letter"


class NoteStatus(str, Enum):
    """Lifecycle status for clinical documentation."""

    DRAFT = "draft"
    FINALIZED = "finalized"
    AMENDED = "amended"


class SOAPSection(BaseModel):
    """Standardized SOAP note sections."""

    subjective: str = Field(..., description="Patient symptoms, chief complaint, and history of present illness")
    objective: str = Field(..., description="Vital signs, physical exam observations, lab and imaging findings")
    assessment: str = Field(..., description="Clinical diagnostic impressions and differential considerations")
    plan: str = Field(..., description="Diagnostic workup, therapy, medications, and follow-up instructions")


class ClinicalNoteCreate(BaseModel):
    """Schema for manual note drafting."""

    title: str = Field(..., min_length=2, max_length=255, description="Descriptive clinical note title")
    note_type: NoteType = Field(default=NoteType.SOAP, description="Category of clinical note")
    encounter_id: Optional[int] = Field(default=None, description="Optional associated encounter ID")
    content_json: Optional[dict[str, Any]] = Field(default=None, description="Structured clinical sections")
    raw_text: str = Field(..., min_length=5, description="Full rendered note narrative")


class ClinicalNoteUpdate(BaseModel):
    """Schema for updating draft clinical notes."""

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    content_json: Optional[dict[str, Any]] = None
    raw_text: Optional[str] = Field(default=None, min_length=5)


class ClinicalNoteSynthesizeRequest(BaseModel):
    """Request schema for triggering AI Scribe note synthesis."""

    patient_id: str = Field(..., description="Patient public identifier (e.g. PAT-20260829-XXXX)")
    note_type: NoteType = Field(default=NoteType.SOAP, description="Target note structure to generate")
    encounter_id: Optional[int] = Field(default=None, description="Associated encounter ID")
    chat_session_id: Optional[str] = Field(default=None, description="Optional chat session ID for transcript synthesis")
    custom_instructions: Optional[str] = Field(default=None, max_length=1000, description="Clinician guidance or specific focus")


class ClinicalNoteSignoff(BaseModel):
    """Physician verification and legal signoff schema."""

    clinician_notes: Optional[str] = Field(default=None, max_length=2000, description="Physician confirmation remarks or addendum")
    confirm_accuracy: bool = Field(..., description="Explicit acknowledgement of clinical review and accuracy")


class ClinicalNoteResponse(BaseModel):
    """Full representation of a clinical note record."""

    id: int
    note_id: str
    patient_id: int
    author_user_id: Optional[int]
    encounter_id: Optional[int]
    title: str
    note_type: NoteType
    status: NoteStatus
    content_json: Optional[dict[str, Any]]
    raw_text: str
    is_ai_generated: bool
    requires_clinician_review: bool
    signed_by_user_id: Optional[int]
    signed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicalNoteListResponse(BaseModel):
    """List response envelope for patient clinical notes."""

    items: list[ClinicalNoteResponse]
    total: int

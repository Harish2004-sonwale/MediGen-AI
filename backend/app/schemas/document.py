from datetime import datetime
from enum import Enum
import math
from typing import Union
from pydantic import BaseModel, ConfigDict, Field


class DocumentType(str, Enum):
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    PRESCRIPTION = "prescription"
    CLINICAL_NOTE = "clinical_note"
    IMAGING_REPORT = "imaging_report"
    OTHER = "other"


class DocumentProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Document title or clinical label")
    document_type: DocumentType = Field(
        default=DocumentType.OTHER,
        description="Clinical classification of the document",
    )
    encounter_id: Union[int, str, None] = Field(
        default=None,
        description="Optional associated clinical encounter ID",
    )


class DocumentCreate(DocumentBase):
    patient_id: Union[int, str] = Field(
        ...,
        description="Target patient ID (database ID or public patient_id like PAT-...)",
    )


class DocumentMetadataUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    document_type: DocumentType | None = None
    encounter_id: Union[int, str, None] = None


class DocumentResponse(BaseModel):
    id: int
    document_id: str
    patient_id: int
    patient_public_id: str
    uploader_user_id: int | None = None
    encounter_id: int | None = None
    title: str
    document_type: DocumentType
    original_filename: str
    file_extension: str
    file_size_bytes: int
    mime_type: str
    processing_status: DocumentProcessingStatus
    error_message: str | None = None
    page_count: int | None = None
    total_chunks: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[DocumentResponse],
        total: int,
        page: int,
        size: int,
    ) -> "DocumentListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )


class DocumentChunkResponse(BaseModel):
    id: int
    chunk_id: str
    document_id: int
    document_public_id: str
    patient_id: int
    chunk_index: int
    page_number: int | None = None
    content: str
    token_count: int | None = None
    vector_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkListResponse(BaseModel):
    items: list[DocumentChunkResponse]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[DocumentChunkResponse],
        total: int,
        page: int,
        size: int,
    ) -> "DocumentChunkListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

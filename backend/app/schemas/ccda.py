"""Pydantic schemas for HL7 C-CDA R2.1 Document Exchange & Parsing."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CCDAExportRequest(BaseModel):
    patient_id: str
    document_type: str = Field(
        default="continuity_of_care_document",
        description="continuity_of_care_document, referral_note, discharge_summary",
    )
    destination_facility_id: Optional[str] = None
    custom_instructions: Optional[str] = None


class CCDAExportResponse(BaseModel):
    document_id: str
    patient_id: str
    document_type: str
    title: str
    created_at: datetime
    sha256_hash: str
    xml_content: str
    section_count: int


class CCDAClinicalItem(BaseModel):
    code: Optional[str] = None
    code_system: Optional[str] = None
    display_name: str
    status: Optional[str] = "active"
    effective_date: Optional[str] = None
    narrative: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None


class CCDASectionData(BaseModel):
    section_title: str
    template_id: str
    items: List[CCDAClinicalItem] = Field(default_factory=list)
    narrative_html: Optional[str] = None


class CCDAImportRequest(BaseModel):
    patient_id: str
    xml_content: str = Field(..., min_length=10)
    source_facility: Optional[str] = "External Healthcare Entity"


class CCDAImportResponse(BaseModel):
    document_id: str
    patient_id: str
    document_type: str
    title: str
    source_facility: str
    sha256_hash: str
    created_at: datetime
    allergies_count: int
    medications_count: int
    problems_count: int
    encounters_count: int
    vitals_count: int
    results_count: int
    sections: List[CCDASectionData] = Field(default_factory=list)
    reconciliation_message: str


class CCDADocumentSummary(BaseModel):
    document_id: str
    patient_id: str
    facility_id: str
    document_type: str
    direction: str
    title: str
    source_facility: Optional[str] = None
    destination_facility: Optional[str] = None
    sha256_hash: str
    section_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CCDADocumentListResponse(BaseModel):
    total: int
    items: List[CCDADocumentSummary]

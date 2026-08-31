"""Pydantic schemas for Clinical Terminology Normalization & Semantic Cross-walks."""

from typing import List, Optional
from pydantic import BaseModel, Field


class TerminologyConcept(BaseModel):
    system: str = Field(..., description="Target system: LOINC, SNOMED_CT, RXNORM, ICD10_CM")
    code: str = Field(..., description="Standardized concept code, e.g. 6298-4, 44054006, 314076")
    display: str = Field(..., description="Standard clinical display title")
    confidence: float = Field(default=1.0, description="Match confidence score between 0.0 and 1.0")
    match_type: str = Field(default="EXACT", description="EXACT, SYNONYM, SEMANTIC_SIMILARITY, UNMAPPED")
    source: str = Field(default="LOCAL_DICTIONARY", description="LOCAL_DICTIONARY or AUTHORITATIVE_SERVER")


class TerminologyNormalizeRequest(BaseModel):
    query: str = Field(..., description="Clinical term, test name, diagnosis or medication to normalize")
    target_system: Optional[str] = Field(None, description="Optional filter: LOINC, SNOMED_CT, RXNORM, ICD10_CM")
    category: Optional[str] = Field(None, description="LAB, CONDITION, MEDICATION, PROCEDURE")


class TerminologyNormalizeResponse(BaseModel):
    query: str
    normalized: Optional[TerminologyConcept] = None
    alternatives: List[TerminologyConcept] = []
    semantic_distance: float = 0.0
    status: str = "SUCCESS"


class TerminologyCrossWalkRequest(BaseModel):
    source_system: str
    source_code: str
    target_system: str


class TerminologyCrossWalkResponse(BaseModel):
    source_system: str
    source_code: str
    target_system: str
    target_code: Optional[str] = None
    target_display: Optional[str] = None
    confidence: float = 0.0
    status: str = "MATCHED"

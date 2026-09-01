"""Pydantic schemas for Enterprise Master Patient Index (EMPI) operations."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EMPIMatchCandidate(BaseModel):
    patient_id: str
    facility_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_grade: str = Field(..., description="exact, probable, possible, distinct")
    feature_scores: Dict[str, float] = Field(default_factory=dict)
    enterprise_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EMPIMatchCandidatesResponse(BaseModel):
    query_patient_id: str
    total_candidates: int
    auto_match_threshold: float = 0.85
    manual_review_threshold: float = 0.65
    candidates: List[EMPIMatchCandidate]


class EMPILinkRequest(BaseModel):
    enterprise_id: Optional[str] = None
    patient_id: str
    target_patient_id: Optional[str] = None
    link_type: str = "manual_link"


class EMPILinkResponse(BaseModel):
    enterprise_id: str
    patient_id: str
    facility_id: str
    match_score: float
    link_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EMPIUnlinkRequest(BaseModel):
    patient_id: str
    reason: Optional[str] = "Manual administrative unlink"


class EMPIMergeRequest(BaseModel):
    target_patient_id: str
    source_patient_id: str
    merge_reason: str = "Duplicate identity resolution"


class EMPIMergeResponse(BaseModel):
    merge_id: str
    target_enterprise_id: str
    source_enterprise_id: str
    target_patient_id: str
    source_patient_id: str
    merged_at: datetime
    message: str


class EMPISplitRequest(BaseModel):
    merge_id: str
    split_reason: Optional[str] = "Revert false positive merge"


class EMPIMatchReviewItem(BaseModel):
    review_id: str
    patient_id_a: str
    patient_id_b: str
    facility_id_a: str
    facility_id_b: str
    match_score: float
    feature_breakdown: Dict[str, Any]
    status: str
    reviewed_by_user_id: Optional[int] = None
    review_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EMPIMatchReviewListResponse(BaseModel):
    total: int
    items: List[EMPIMatchReviewItem]


class EMPIMatchReviewActionRequest(BaseModel):
    action: str = Field(..., description="approve_link, approve_merge, reject_distinct")
    notes: Optional[str] = None


class FHIRPatientMatchRequest(BaseModel):
    resource: Dict[str, Any] = Field(..., description="FHIR R4 Patient Resource")
    only_certain_matches: bool = False
    count: int = 10

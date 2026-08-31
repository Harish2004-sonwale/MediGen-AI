"""API Endpoints for Clinical Terminology Normalization and Semantic Cross-Walks."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.terminology import (
    TerminologyCrossWalkRequest,
    TerminologyCrossWalkResponse,
    TerminologyNormalizeRequest,
    TerminologyNormalizeResponse,
)
from app.services.terminology_service import terminology_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/normalize", response_model=TerminologyNormalizeResponse, summary="Normalize Clinical Concept")
def normalize_clinical_term(payload: TerminologyNormalizeRequest) -> TerminologyNormalizeResponse:
    """Normalizes unstructured or proprietary clinical terms to standard LOINC, SNOMED CT, or RxNorm codes."""
    return terminology_service.normalize_term(payload)


@router.post("/crosswalk", response_model=TerminologyCrossWalkResponse, summary="Vocabulary Cross-Walk")
def crosswalk_clinical_code(payload: TerminologyCrossWalkRequest) -> TerminologyCrossWalkResponse:
    """Translates codes across standard vocabularies (e.g. ICD-10 to SNOMED CT)."""
    return terminology_service.cross_walk(payload)

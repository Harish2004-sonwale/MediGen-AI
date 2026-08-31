"""Service for Clinical Terminology Normalization, Semantic Distance and Cross-Walks."""

from difflib import SequenceMatcher
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.terminology import (
    TerminologyConcept,
    TerminologyCrossWalkRequest,
    TerminologyCrossWalkResponse,
    TerminologyNormalizeRequest,
    TerminologyNormalizeResponse,
)

logger = logging.getLogger(__name__)

# Curated offline deterministic dictionary for top clinical concepts across LOINC, SNOMED CT, RxNorm, and ICD-10-CM
OFFLINE_CONCEPT_DICTIONARY: List[Dict[str, Any]] = [
    # Laboratory & Vitals (LOINC)
    {"query_synonyms": ["potassium", "serum potassium", "k level", "potassium blood"], "system": "LOINC", "code": "6298-4", "display": "Potassium [Moles/volume] in Blood", "category": "LAB"},
    {"query_synonyms": ["sodium", "serum sodium", "na level", "sodium blood"], "system": "LOINC", "code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma", "category": "LAB"},
    {"query_synonyms": ["hemoglobin a1c", "hba1c", "glycated hemoglobin", "a1c"], "system": "LOINC", "code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood", "category": "LAB"},
    {"query_synonyms": ["creatinine", "serum creatinine", "kidney function test"], "system": "LOINC", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma", "category": "LAB"},
    {"query_synonyms": ["glucose", "blood glucose", "fasting blood sugar", "fbs"], "system": "LOINC", "code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma", "category": "LAB"},
    {"query_synonyms": ["heart rate", "pulse", "bpm", "cardiac rate"], "system": "LOINC", "code": "8867-4", "display": "Heart rate", "category": "VITAL"},
    {"query_synonyms": ["systolic blood pressure", "sbp", "systolic bp"], "system": "LOINC", "code": "8480-6", "display": "Systolic blood pressure", "category": "VITAL"},
    {"query_synonyms": ["diastolic blood pressure", "dbp", "diastolic bp"], "system": "LOINC", "code": "8462-4", "display": "Diastolic blood pressure", "category": "VITAL"},
    {"query_synonyms": ["oxygen saturation", "spo2", "pulse ox", "oximetry"], "system": "LOINC", "code": "2708-6", "display": "Oxygen saturation in Arterial blood by Pulse oximetry", "category": "VITAL"},

    # Clinical Findings & Diagnoses (SNOMED CT & ICD-10-CM)
    {"query_synonyms": ["type 2 diabetes", "diabetes mellitus type 2", "t2d", "t2dm", "adult onset diabetes"], "system": "SNOMED_CT", "code": "44054006", "display": "Type 2 diabetes mellitus (disorder)", "category": "CONDITION"},
    {"query_synonyms": ["essential hypertension", "high blood pressure", "htn", "systemic hypertension"], "system": "SNOMED_CT", "code": "59621000", "display": "Essential hypertension (disorder)", "category": "CONDITION"},
    {"query_synonyms": ["congestive heart failure", "chf", "heart failure"], "system": "SNOMED_CT", "code": "84114007", "display": "Heart failure (disorder)", "category": "CONDITION"},
    {"query_synonyms": ["atrial fibrillation", "a-fib", "afib"], "system": "SNOMED_CT", "code": "49436004", "display": "Atrial fibrillation (disorder)", "category": "CONDITION"},
    {"query_synonyms": ["chronic kidney disease", "ckd", "renal impairment"], "system": "SNOMED_CT", "code": "709044004", "display": "Chronic kidney disease (disorder)", "category": "CONDITION"},
    {"query_synonyms": ["major depressive disorder", "mdd", "clinical depression"], "system": "SNOMED_CT", "code": "370143000", "display": "Major depressive disorder (disorder)", "category": "CONDITION"},

    # Medications (RxNorm)
    {"query_synonyms": ["lisinopril", "prinivil", "zestril", "lisinopril 10 mg"], "system": "RXNORM", "code": "314076", "display": "Lisinopril 10 MG Oral Tablet", "category": "MEDICATION"},
    {"query_synonyms": ["metformin", "glucophage", "metformin 500 mg"], "system": "RXNORM", "code": "860975", "display": "Metformin hydrochloride 500 MG Oral Tablet", "category": "MEDICATION"},
    {"query_synonyms": ["atorvastatin", "lipitor", "atorvastatin 20 mg"], "system": "RXNORM", "code": "617314", "display": "Atorvastatin 20 MG Oral Tablet", "category": "MEDICATION"},
    {"query_synonyms": ["warfarin", "coumadin", "jantoven", "warfarin 5 mg"], "system": "RXNORM", "code": "855332", "display": "Warfarin sodium 5 MG Oral Tablet", "category": "MEDICATION"},
    {"query_synonyms": ["amoxicillin", "amoxil", "amoxicillin 500 mg"], "system": "RXNORM", "code": "308189", "display": "Amoxicillin 500 MG Oral Tablet", "category": "MEDICATION"},
    {"query_synonyms": ["levothyroxine", "synthroid", "levoxyl"], "system": "RXNORM", "code": "966224", "display": "Levothyroxine sodium 50 MCG Oral Tablet", "category": "MEDICATION"},
]

# Cross-walk lookup matrix (ICD-10 <-> SNOMED CT <-> RxNorm)
CROSS_WALK_REGISTRY: Dict[Tuple[str, str, str], Tuple[str, str, float]] = {
    ("ICD10", "E11.9", "SNOMED_CT"): ("44054006", "Type 2 diabetes mellitus (disorder)", 0.98),
    ("ICD10", "I10", "SNOMED_CT"): ("59621000", "Essential hypertension (disorder)", 0.99),
    ("ICD10", "I50.9", "SNOMED_CT"): ("84114007", "Heart failure (disorder)", 0.95),
    ("ICD10", "I48.91", "SNOMED_CT"): ("49436004", "Atrial fibrillation (disorder)", 0.98),
    ("ICD10", "N18.9", "SNOMED_CT"): ("709044004", "Chronic kidney disease (disorder)", 0.96),
    ("SNOMED_CT", "44054006", "ICD10"): ("E11.9", "Type 2 diabetes mellitus without complications", 0.98),
    ("SNOMED_CT", "59621000", "ICD10"): ("I10", "Essential (primary) hypertension", 0.99),
}


class TerminologyService:
    """Clinical Terminology Normalization & Semantic Mapping Service."""

    def _clean_text(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9\s]", "", text.lower()).strip()

    def normalize_term(self, request: TerminologyNormalizeRequest) -> TerminologyNormalizeResponse:
        """Normalizes a free-text clinical query into standardized LOINC, SNOMED CT, or RxNorm concepts."""
        clean_q = self._clean_text(request.query)
        candidates: List[Tuple[float, Dict[str, Any], str]] = []

        for item in OFFLINE_CONCEPT_DICTIONARY:
            if request.target_system and item["system"].upper() != request.target_system.upper():
                continue
            if request.category and item.get("category", "").upper() != request.category.upper():
                continue

            # Check exact synonym match
            exact_match = False
            for syn in item["query_synonyms"]:
                clean_syn = self._clean_text(syn)
                if clean_q == clean_syn:
                    candidates.append((1.0, item, "EXACT"))
                    exact_match = True
                    break
                elif clean_q in clean_syn or clean_syn in clean_q:
                    ratio = SequenceMatcher(None, clean_q, clean_syn).ratio()
                    score = max(0.85, ratio)
                    candidates.append((score, item, "SYNONYM"))
                    exact_match = True
                    break

            if not exact_match:
                # Fuzzy sequence matching against display name
                clean_display = self._clean_text(item["display"])
                ratio = SequenceMatcher(None, clean_q, clean_display).ratio()
                if ratio >= 0.40:
                    candidates.append((ratio, item, "SEMANTIC_SIMILARITY"))

        # Sort candidates descending by confidence score
        candidates.sort(key=lambda x: x[0], reverse=True)

        if not candidates:
            # Return unmapped fallback
            return TerminologyNormalizeResponse(
                query=request.query,
                normalized=TerminologyConcept(
                    system=request.target_system or "LOCAL",
                    code="UNMAPPED",
                    display=request.query,
                    confidence=0.0,
                    match_type="UNMAPPED",
                    source="LOCAL_DICTIONARY",
                ),
                alternatives=[],
                semantic_distance=1.0,
                status="NO_MATCH",
            )

        best_score, best_item, best_type = candidates[0]
        primary_concept = TerminologyConcept(
            system=best_item["system"],
            code=best_item["code"],
            display=best_item["display"],
            confidence=round(best_score, 3),
            match_type=best_type,
            source="LOCAL_DICTIONARY",
        )

        alternatives: List[TerminologyConcept] = []
        for score, alt_item, alt_type in candidates[1:4]:
            alternatives.append(
                TerminologyConcept(
                    system=alt_item["system"],
                    code=alt_item["code"],
                    display=alt_item["display"],
                    confidence=round(score, 3),
                    match_type=alt_type,
                    source="LOCAL_DICTIONARY",
                )
            )

        return TerminologyNormalizeResponse(
            query=request.query,
            normalized=primary_concept,
            alternatives=alternatives,
            semantic_distance=round(1.0 - best_score, 3),
            status="SUCCESS",
        )

    def cross_walk(self, request: TerminologyCrossWalkRequest) -> TerminologyCrossWalkResponse:
        """Translates codes across standard vocabularies (e.g. ICD-10 to SNOMED CT)."""
        key = (
            request.source_system.upper().replace("-", "_"),
            request.source_code.strip(),
            request.target_system.upper().replace("-", "_"),
        )
        if key in CROSS_WALK_REGISTRY:
            tgt_code, tgt_display, conf = CROSS_WALK_REGISTRY[key]
            return TerminologyCrossWalkResponse(
                source_system=request.source_system,
                source_code=request.source_code,
                target_system=request.target_system,
                target_code=tgt_code,
                target_display=tgt_display,
                confidence=conf,
                status="MATCHED",
            )

        return TerminologyCrossWalkResponse(
            source_system=request.source_system,
            source_code=request.source_code,
            target_system=request.target_system,
            target_code=None,
            target_display=None,
            confidence=0.0,
            status="UNMAPPED",
        )


terminology_service = TerminologyService()

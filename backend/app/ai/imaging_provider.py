from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Optional

from app.schemas.media import ImagingFindingItem, MediaModality, StructuredImagingFinding


class BaseMedicalImagingProvider(ABC):
    """Base interface for legacy media diagnostics analysis (Phase 9.0.7)."""

    @abstractmethod
    def analyze_image(
        self,
        file_path: str,
        modality: MediaModality,
        **kwargs: Any,
    ) -> StructuredImagingFinding:
        """Analyze diagnostic media and return structured findings."""
        pass


class MockMedicalImagingProvider(BaseMedicalImagingProvider):
    """Deterministic offline mock provider for legacy media diagnostics."""

    def analyze_image(
        self,
        file_path: str,
        modality: MediaModality,
        **kwargs: Any,
    ) -> StructuredImagingFinding:
        """Return deterministic findings based on modality."""
        if modality == MediaModality.XRAY_CHEST:
            return StructuredImagingFinding(
                modality=modality,
                confidence_score=0.88,
                primary_observation="Mild opacity in the right lower lobe consistent with early infiltrate.",
                findings=[
                    ImagingFindingItem(
                        observation="Focal consolidation",
                        anatomical_region="Right lower lobe",
                        confidence=0.89,
                        is_abnormal=True,
                        severity="Moderate",
                    ),
                    ImagingFindingItem(
                        observation="Normal cardiac silhouette",
                        anatomical_region="Cardiomediastinum",
                        confidence=0.95,
                        is_abnormal=False,
                        severity="Normal",
                    ),
                ],
                differential_notes=["Community-acquired pneumonia", "Atelectasis"],
            )
        elif modality == MediaModality.CT_SCAN:
            return StructuredImagingFinding(
                modality=modality,
                confidence_score=0.91,
                primary_observation="No acute intracranial hemorrhage or midline shift.",
                findings=[
                    ImagingFindingItem(
                        observation="Intact parenchymal attenuation",
                        anatomical_region="Cerebral hemispheres",
                        confidence=0.94,
                        is_abnormal=False,
                        severity="Normal",
                    ),
                ],
                differential_notes=["Normal age-appropriate brain CT"],
            )
        else:
            return StructuredImagingFinding(
                modality=modality,
                confidence_score=0.85,
                primary_observation="Visual patterns evaluated within expected parameters.",
                findings=[
                    ImagingFindingItem(
                        observation="Standard anatomical morphology",
                        anatomical_region="Target zone",
                        confidence=0.85,
                        is_abnormal=False,
                        severity="Normal",
                    ),
                ],
                differential_notes=["Benign or normal variation"],
            )


def get_imaging_provider() -> BaseMedicalImagingProvider:
    """Factory returning configured imaging provider."""
    return MockMedicalImagingProvider()



def _sanitize_untrusted_text(text: Optional[str]) -> str:
    """Sanitize untrusted clinical input to prevent prompt injection and hallucination triggers."""
    if not text:
        return ""
    # Strip dangerous control characters and instruction override delimiters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    sanitized = sanitized.replace("```", "'''")
    # Neutralize prompt injection phrases
    injection_patterns = [
        r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions",
        r"(?i)disregard\s+(all\s+)?guidelines",
        r"(?i)you\s+are\s+now\s+in\s+unrestricted\s+mode",
        r"(?i)system\s+prompt:",
    ]
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[FILTERED_UNTRUSTED_INSTRUCTION]", sanitized)
    return sanitized.strip()


def _compute_sha256(data: Any) -> str:
    """Compute deterministic SHA-256 hash across canonical JSON structure."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class BaseImagingAIProvider(ABC):
    """Abstract base class for assistive medical imaging AI interpretation providers."""

    @abstractmethod
    def interpret_study(
        self,
        study_data: dict[str, Any],
        multimodal_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform multimodal AI interpretation on an imaging study."""
        pass


class MockImagingAIProvider(BaseImagingAIProvider):
    """Deterministic, offline, zero-dependency medical imaging AI interpretation provider."""

    def __init__(self, provider_version: str = "1.0.0-mock-imaging"):
        self.provider_version = provider_version

    def interpret_study(
        self,
        study_data: dict[str, Any],
        multimodal_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate deterministic, clinical-grade imaging findings and draft report."""
        study_id = study_data.get("study_id", "STU-001")
        modality = str(study_data.get("modality", "XRAY")).upper()
        body_site = str(study_data.get("body_site", "CHEST")).upper()
        description = _sanitize_untrusted_text(study_data.get("study_description", ""))
        indication = _sanitize_untrusted_text(multimodal_context.get("clinical_indication", description))

        # Contextual signals
        text_corpus = f"{description} {indication}".lower()
        diagnoses = [d.lower() for d in multimodal_context.get("active_diagnoses", [])]
        diagnoses_corpus = " ".join(diagnoses)
        recent_vitals = multimodal_context.get("recent_vitals", [])
        prev_studies = multimodal_context.get("previous_studies", [])

        # Vitals inspection
        hypoxic = any(v.get("spo2") and v.get("spo2") < 92 for v in recent_vitals)
        tachycardic = any(v.get("heart_rate") and v.get("heart_rate") > 110 for v in recent_vitals)
        feverish = any(v.get("temperature") and v.get("temperature") > 38.5 for v in recent_vitals)

        findings: list[dict[str, Any]] = []

        # ---------------------------------------------------------------------
        # 1. Modality & Anatomy Specific Diagnostic Heuristics
        # ---------------------------------------------------------------------
        if modality == "CT" and body_site == "HEAD_BRAIN":
            if any(k in text_corpus for k in ["headache", "fall", "trauma", "stroke", "bleed", "hemorrhage", "syncope", "altered"]):
                findings.append({
                    "finding_type": "POSSIBLE_HEMORRHAGE",
                    "anatomical_location": "Right Basal Ganglia / Temporal Lobe",
                    "laterality": "RIGHT",
                    "severity": "CRITICAL",
                    "confidence_score": 0.94,
                    "is_critical": True,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Hyperdense focus measuring approx 18mm suspicious for acute parenchymal intracranial hemorrhage. Surrounding vasogenic edema noted.",
                    "recommendation": "POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW. Recommend stat neurosurgical consultation and follow-up non-contrast head CT.",
                    "bounding_box_json": {"x": 210, "y": 185, "width": 65, "height": 70},
                })
            else:
                findings.append({
                    "finding_type": "NORMAL_APPEARANCE",
                    "anatomical_location": "Cerebral Hemispheres and Ventricles",
                    "laterality": "BILATERAL",
                    "severity": "NORMAL",
                    "confidence_score": 0.96,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Normal brain parenchyma without acute intracranial hemorrhage, midline shift, or mass effect. Ventricles and sulci age-appropriate.",
                    "recommendation": "Routine clinical correlation as indicated.",
                    "bounding_box_json": None,
                })

        elif modality in ("XRAY", "CT") and body_site == "CHEST":
            if any(k in text_corpus for k in ["pneumothorax", "chest pain", "dyspnea", "sob", "shortness of breath"]) and "pneumothorax" in text_corpus:
                findings.append({
                    "finding_type": "POSSIBLE_EFFUSION",
                    "anatomical_location": "Left Pleural Space",
                    "laterality": "LEFT",
                    "severity": "CRITICAL",
                    "confidence_score": 0.92,
                    "is_critical": True,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Peripheral lucency in the left hemithorax with visceral pleural line displacement, consistent with acute pneumothorax.",
                    "recommendation": "POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW. Immediate clinician evaluation for chest tube decompression.",
                    "bounding_box_json": {"x": 80, "y": 120, "width": 110, "height": 220},
                })
            elif any(k in text_corpus for k in ["cough", "fever", "pneumonia", "infiltrate", "consolidation", "infection"]) or feverish or hypoxic:
                findings.append({
                    "finding_type": "POSSIBLE_PNEUMONIA",
                    "anatomical_location": "Right Lower Lobe",
                    "laterality": "RIGHT",
                    "severity": "SEVERE" if hypoxic else "MODERATE",
                    "confidence_score": 0.89,
                    "is_critical": True if hypoxic else False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Focal airspace consolidation with air bronchograms in the right lower lobe, suspicious for acute bacterial pneumonia.",
                    "recommendation": "Clinical correlation with sputum cultures, inflammatory markers, and antimicrobial therapy as clinically indicated.",
                    "bounding_box_json": {"x": 260, "y": 320, "width": 140, "height": 130},
                })
                findings.append({
                    "finding_type": "POSSIBLE_EFFUSION",
                    "anatomical_location": "Right Costophrenic Angle",
                    "laterality": "RIGHT",
                    "severity": "MILD",
                    "confidence_score": 0.82,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Blunting of the right costophrenic sulcus indicative of a small parapneumonic pleural effusion.",
                    "recommendation": "Monitor with follow-up chest radiography following medical treatment.",
                    "bounding_box_json": {"x": 280, "y": 420, "width": 90, "height": 60},
                })
            elif any(k in text_corpus for k in ["nodule", "mass", "lesion", "screening", "smoker", "oncology", "cancer"]) or "cancer" in diagnoses_corpus:
                findings.append({
                    "finding_type": "POSSIBLE_NODULE",
                    "anatomical_location": "Left Upper Lobe",
                    "laterality": "LEFT",
                    "severity": "MODERATE",
                    "confidence_score": 0.86,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Well-circumscribed non-calcified pulmonary nodule measuring 8mm in the left upper lobe apicoposterior segment.",
                    "recommendation": "Recommend high-resolution non-contrast chest CT surveillance at 3-6 months per Fleischner Society guidelines.",
                    "bounding_box_json": {"x": 150, "y": 140, "width": 45, "height": 45},
                })
            else:
                findings.append({
                    "finding_type": "NORMAL_APPEARANCE",
                    "anatomical_location": "Bilateral Lungs and Cardiomediastinal Silhouette",
                    "laterality": "BILATERAL",
                    "severity": "NORMAL",
                    "confidence_score": 0.95,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Lungs are clear without focal consolidation, pneumothorax, or pleural effusion. Cardiomediastinal silhouette is within normal limits.",
                    "recommendation": "No acute cardiopulmonary process identified.",
                    "bounding_box_json": None,
                })

        elif modality in ("XRAY", "CT", "MRI") and body_site in ("EXTREMITY", "SPINE"):
            if any(k in text_corpus for k in ["trauma", "fall", "pain", "swelling", "fracture", "deformity", "mva", "injury"]):
                findings.append({
                    "finding_type": "POSSIBLE_FRACTURE",
                    "anatomical_location": f"{body_site.title()} Cortical Margin",
                    "laterality": "RIGHT" if "right" in text_corpus else "LEFT" if "left" in text_corpus else "MIDLINE",
                    "severity": "MODERATE",
                    "confidence_score": 0.91,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": f"AI-assisted finding: Linear cortical disruption with minimal displacement identified in the {body_site.lower()} region.",
                    "recommendation": "Orthopedic evaluation and immobilization as clinically warranted.",
                    "bounding_box_json": {"x": 180, "y": 200, "width": 75, "height": 85},
                })
            else:
                findings.append({
                    "finding_type": "NORMAL_APPEARANCE",
                    "anatomical_location": f"{body_site.title()} Osseous Structures",
                    "laterality": "NOT_APPLICABLE",
                    "severity": "NORMAL",
                    "confidence_score": 0.94,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Intact cortical margins with preserved joint spaces. No acute fracture or dislocation seen.",
                    "recommendation": "Routine clinical correlation.",
                    "bounding_box_json": None,
                })

        elif modality in ("CT", "ULTRASOUND", "MRI") and body_site in ("ABDOMEN", "PELVIS"):
            if any(k in text_corpus for k in ["pain", "appendicitis", "cholecystitis", "mass", "obstruction", "stone", "hematoma"]):
                findings.append({
                    "finding_type": "POSSIBLE_MASS" if "mass" in text_corpus else "OTHER_ABNORMALITY",
                    "anatomical_location": "Right Lower Quadrant / Right Upper Quadrant",
                    "laterality": "RIGHT",
                    "severity": "MODERATE",
                    "confidence_score": 0.88,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Mural thickening and regional inflammatory stranding identified. No free intraperitoneal air.",
                    "recommendation": "Correlate with acute abdominal exam and targeted surgical consult if peritoneal signs develop.",
                    "bounding_box_json": {"x": 220, "y": 310, "width": 95, "height": 90},
                })
            else:
                findings.append({
                    "finding_type": "NORMAL_APPEARANCE",
                    "anatomical_location": "Abdominal and Pelvic Viscera",
                    "laterality": "BILATERAL",
                    "severity": "NORMAL",
                    "confidence_score": 0.93,
                    "is_critical": False,
                    "finding_nature": "AI_GENERATED_FINDING",
                    "description": "AI-assisted finding: Solid abdominal organs demonstrate normal attenuation and morphology without focal mass or acute inflammatory changes.",
                    "recommendation": "No acute abdominal pathology detected.",
                    "bounding_box_json": None,
                })

        else:
            findings.append({
                "finding_type": "NORMAL_APPEARANCE",
                "anatomical_location": f"{body_site.title()} Region",
                "laterality": "NOT_APPLICABLE",
                "severity": "NORMAL",
                "confidence_score": 0.90,
                "is_critical": False,
                "finding_nature": "AI_GENERATED_FINDING",
                "description": f"AI-assisted finding: General morphology of {body_site.lower()} within expected anatomical limits for age.",
                "recommendation": "Clinical correlation recommended.",
                "bounding_box_json": None,
            })

        # Calculate cryptographic provenance hashes for each finding
        for idx, f in enumerate(findings):
            ftype = f["finding_type"]
            f_hash = hashlib.sha256(f"{study_id}-{idx}-{ftype}".encode()).hexdigest()[:8].upper()
            f["finding_id"] = f"FND-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{f_hash}"
            f["provenance_hash"] = _compute_sha256({
                "study_id": study_id,
                "finding_type": f["finding_type"],
                "location": f["anatomical_location"],
                "confidence": f["confidence_score"],
                "provider_version": self.provider_version,
            })


        # ---------------------------------------------------------------------
        # 2. Draft Structured Radiology Report Synthesis
        # ---------------------------------------------------------------------
        critical_findings = [f for f in findings if f.get("is_critical")]
        has_critical = len(critical_findings) > 0

        technique_str = f"{modality} examination of the {body_site.replace('_', ' ').title()} performed utilizing standard institutional diagnostic acquisition protocols."

        comparison_str = "None available for prior comparison."
        if prev_studies:
            prior_dates = [p.get("study_datetime", "prior date") for p in prev_studies[:2]]
            comparison_str = f"Compared with previous imaging studies dated {', '.join(str(d) for d in prior_dates)}."

        findings_narrative = "\n".join(f"- {f['anatomical_location']} ({f['laterality']}): {f['description']}" for f in findings)

        impression_narrative = "\n".join(f"{idx+1}. {f['finding_type'].replace('_', ' ').title()}: {f['description']}" for idx, f in enumerate(findings))


        recommendations_narrative = "\n".join(f"- {f['recommendation']}" for f in findings)

        crit_summary = None
        if has_critical:
            crit_summary = (
                f"POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW: "
                f"{'; '.join(cf['description'] for cf in critical_findings)}"
            )

        draft_report = {
            "status": "AI_ASSISTED",
            "clinical_indication": indication or "Diagnostic evaluation.",
            "technique": technique_str,
            "comparison_studies": comparison_str,
            "findings": findings_narrative,
            "impression": impression_narrative,
            "recommendations": recommendations_narrative,
            "critical_findings_summary": crit_summary,
            "is_critical": has_critical,
            "ai_assistance_metadata_json": {
                "ai_provider": "MockImagingAIProvider",
                "provider_version": self.provider_version,
                "inference_timestamp": datetime.now(timezone.utc).isoformat(),
                "findings_count": len(findings),
                "critical_findings_count": len(critical_findings),
                "safety_disclaimer": "Assistive AI decision support only. Requires formal radiologist/clinician review and signature.",
                "multimodal_inputs": {
                    "vitals_considered": len(recent_vitals),
                    "diagnoses_considered": len(diagnoses),
                    "previous_studies_compared": len(prev_studies),
                },
            },
        }
        draft_report["provenance_hash"] = _compute_sha256({
            "study_id": study_id,
            "findings_count": len(findings),
            "is_critical": has_critical,
            "impression": impression_narrative,
            "provider_version": self.provider_version,
        })

        return {
            "study_id": study_id,
            "status": "COMPLETED",
            "findings": findings,
            "draft_report": draft_report,
            "findings_count": len(findings),
            "critical_findings_count": len(critical_findings),
            "provenance_hash": _compute_sha256({
                "study_id": study_id,
                "findings": [f["finding_id"] for f in findings],
                "draft_report_hash": draft_report["provenance_hash"],
            }),
            "evaluated_at": datetime.now(timezone.utc),
        }

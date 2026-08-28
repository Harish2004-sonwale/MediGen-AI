"""Clinical Safety & Decision Support Service.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
Performs modular clinical decision-support safety checks:
1. Medication duplication detection
2. Known allergy conflict warnings
3. Drug-drug interaction (DDI) checking via pluggable providers
4. Condition-drug contraindication checking via pluggable providers

All safety alerts require clinician review and never replace medical judgment.
"""

import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.safety_providers import (
    get_contraindication_provider,
    get_drug_interaction_provider,
)
from app.models.document import DocumentChunk, MedicalDocument
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.schemas.rag import RAGCitation
from app.schemas.safety import (
    ClinicalSafetyAlert,
    ClinicalSafetyReport,
    SafetyAlertType,
    SafetyCheckRequest,
    SafetySeverity,
)
from app.services.rag_service import validate_patient_rag_access

logger = logging.getLogger("medigen.safety")


def _generate_alert_id() -> str:
    """Generate unique clinical safety alert ID."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"ALT-{date_part}-{unique_part}"


def _normalize_med_name(raw_med: str) -> str:
    """Extract primary active medication stem (strip dosage, frequency, forms)."""
    clean = re.sub(r"\b(?:\d+mg|\d+mcg|\d+g|\d+ml|daily|bid|tid|qid|prn|po|oral|tablet|tablets|capsule|capsules|inhaler|puffs?)\b", "", raw_med, flags=re.IGNORECASE)
    clean = re.sub(r"[^\w\s]", " ", clean)
    words = [w.strip().lower() for w in clean.split() if len(w.strip()) > 2]
    return words[0] if words else raw_med.strip().lower()


def evaluate_patient_safety(
    db: Session,
    patient_id_str: str,
    current_user: User,
    request: Optional[SafetyCheckRequest] = None,
    ddi_provider_type: str = "mock",
    contra_provider_type: str = "mock",
) -> ClinicalSafetyReport:
    """Analyze authorized patient medical records and candidate inputs for clinical safety conflicts."""
    from app.services.appointment_service import resolve_patient

    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise KeyError(f"Patient '{patient_id_str}' not found.")

    validate_patient_rag_access(db, current_user, patient)

    candidate_meds = request.candidate_medications if request and request.candidate_medications else []
    candidate_conds = request.active_conditions if request and request.active_conditions else []

    extracted_meds: list[dict] = []  # dict with keys: 'raw', 'normalized', 'citation'
    extracted_allergies: list[dict] = []
    extracted_conditions: list[dict] = []

    # 1. Inspect Encounters for Diagnoses / Conditions
    encounters = db.scalars(
        select(Encounter).where(Encounter.patient_id == patient.id)
    ).all()
    for enc in encounters:
        if enc.chief_complaint:
            extracted_conditions.append({
                "condition": enc.chief_complaint,
                "source": f"Encounter {enc.encounter_type}",
                "citation": None,
            })

    # 2. Inspect Documents & Chunks for Medications, Allergies, and Diagnoses
    documents = db.scalars(
        select(MedicalDocument).where(MedicalDocument.patient_id == patient.id)
    ).all()

    for doc in documents:
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        ).all()
        for chunk in chunks:
            content = chunk.content
            citation = RAGCitation(
                document_id=doc.document_id,
                title=doc.title,
                page_number=chunk.page_number,
                chunk_id=chunk.chunk_id,
                document_type=doc.document_type,
            )

            # Extract Medications
            med_matches = re.finditer(
                r"(?:prescribed|discharge medications?|medications?|rx)\s*:\s*([^\n\.;]+)",
                content,
                re.IGNORECASE,
            )
            for m in med_matches:
                med_str = m.group(1).strip()
                # Split comma separated meds if present
                for single_med in re.split(r",|\band\b", med_str):
                    s_clean = single_med.strip()
                    if len(s_clean) >= 3:
                        extracted_meds.append({
                            "raw": s_clean,
                            "normalized": _normalize_med_name(s_clean),
                            "citation": citation,
                        })

            # Extract Allergies
            allergy_matches = re.finditer(
                r"(?:allergies|allergic to|known allergies)\s*:\s*([^\n\.;]+)",
                content,
                re.IGNORECASE,
            )
            for m in allergy_matches:
                allergy_str = m.group(1).strip()
                if "nkda" not in allergy_str.lower() and "none" not in allergy_str.lower():
                    for single_all in re.split(r",|\band\b", allergy_str):
                        a_clean = single_all.strip()
                        if len(a_clean) >= 3:
                            extracted_allergies.append({
                                "allergy": a_clean,
                                "citation": citation,
                            })

            # Extract Conditions
            diag_matches = re.finditer(
                r"(?:diagnosis|diagnoses|impression|assessment|condition)\s*:\s*([^\n\.;]+)",
                content,
                re.IGNORECASE,
            )
            for m in diag_matches:
                diag_str = m.group(1).strip()
                if len(diag_str) >= 3:
                    extracted_conditions.append({
                        "condition": diag_str,
                        "source": doc.title,
                        "citation": citation,
                    })

    # Add candidate medications & conditions from request payload
    for c_med in candidate_meds:
        extracted_meds.append({
            "raw": c_med.strip(),
            "normalized": _normalize_med_name(c_med),
            "citation": None,
        })
    for c_cond in candidate_conds:
        extracted_conditions.append({
            "condition": c_cond.strip(),
            "source": "Clinical Safety Check Request",
            "citation": None,
        })

    alerts: list[ClinicalSafetyAlert] = []
    generated_now = datetime.now(timezone.utc)

    # ----------------------------------------------------
    # Check A: Medication Duplication
    # ----------------------------------------------------
    meds_by_normalized = defaultdict(list)
    for item in extracted_meds:
        norm = item["normalized"]
        if norm and len(norm) >= 3:
            meds_by_normalized[norm].append(item)

    for norm_name, items in meds_by_normalized.items():
        if len(items) > 1:
            raw_names = list({it["raw"] for it in items})
            citations = [it["citation"] for it in items if it["citation"]]
            # deduplicate citations by chunk_id
            unique_citations = {c.chunk_id: c for c in citations if c.chunk_id}.values()

            alerts.append(
                ClinicalSafetyAlert(
                    alert_id=_generate_alert_id(),
                    patient_id=patient_id_str,
                    alert_type=SafetyAlertType.MEDICATION_DUPLICATE,
                    severity=SafetySeverity.MODERATE,
                    title=f"Potential Medication Duplication: {norm_name.capitalize()}",
                    explanation=(
                        f"Multiple active or candidate medication entries identified for '{norm_name.capitalize()}' "
                        f"({', '.join(raw_names)}). Potential duplicate therapy. Clinician review required."
                    ),
                    medications=raw_names,
                    source_references=["ISMP Medication Safety Guidelines"],
                    generated_at=generated_now,
                    provider="MediGenCDS-Deduplicator",
                    requires_clinician_review=True,
                    citations=list(unique_citations),
                )
            )

    # ----------------------------------------------------
    # Check B: Allergy Warnings
    # ----------------------------------------------------
    for all_item in extracted_allergies:
        allergen = all_item["allergy"].lower().strip()
        for med_item in extracted_meds:
            med_raw = med_item["raw"].lower().strip()
            med_norm = med_item["normalized"].lower().strip()

            # Direct match or cross-reactivity check
            if allergen in med_raw or allergen in med_norm or med_norm in allergen:
                citations = []
                if all_item["citation"]:
                    citations.append(all_item["citation"])
                if med_item["citation"]:
                    citations.append(med_item["citation"])
                unique_citations = {c.chunk_id: c for c in citations if c.chunk_id}.values()

                alerts.append(
                    ClinicalSafetyAlert(
                        alert_id=_generate_alert_id(),
                        patient_id=patient_id_str,
                        alert_type=SafetyAlertType.ALLERGY_WARNING,
                        severity=SafetySeverity.CRITICAL,
                        title=f"Documented Allergy Conflict: {all_item['allergy'].capitalize()} vs {med_item['raw']}",
                        explanation=(
                            f"Patient has documented allergy to '{all_item['allergy']}'. "
                            f"Prescribed or candidate medication '{med_item['raw']}' presents high risk of adverse hypersensitivity reaction."
                        ),
                        medications=[med_item["raw"]],
                        source_references=["Joint Task Force on Allergy Practice Parameters"],
                        generated_at=generated_now,
                        provider="MediGenCDS-AllergyRuleEngine",
                        requires_clinician_review=True,
                        citations=list(unique_citations),
                    )
                )

    # ----------------------------------------------------
    # Check C: Drug-Drug Interactions (Pluggable Provider)
    # ----------------------------------------------------
    all_med_names = list({m["raw"] for m in extracted_meds})
    ddi_provider = get_drug_interaction_provider(ddi_provider_type)
    ddi_results = ddi_provider.check_interactions(all_med_names)

    for ddi in ddi_results:
        # Find citations for involved drugs
        involved_citations = []
        for m in extracted_meds:
            if ddi.drug_a.lower() in m["raw"].lower() or ddi.drug_b.lower() in m["raw"].lower():
                if m["citation"]:
                    involved_citations.append(m["citation"])
        unique_citations = {c.chunk_id: c for c in involved_citations if c.chunk_id}.values()

        alerts.append(
            ClinicalSafetyAlert(
                alert_id=_generate_alert_id(),
                patient_id=patient_id_str,
                alert_type=SafetyAlertType.DRUG_INTERACTION,
                severity=ddi.severity,
                title=ddi.title,
                explanation=ddi.explanation,
                medications=[ddi.drug_a, ddi.drug_b],
                source_references=[ddi.clinical_reference],
                generated_at=generated_now,
                provider=f"MediGenCDS-DDI-{ddi_provider_type}",
                requires_clinician_review=True,
                citations=list(unique_citations),
            )
        )

    # ----------------------------------------------------
    # Check D: Condition-Drug Contraindications (Pluggable Provider)
    # ----------------------------------------------------
    all_condition_names = list({c["condition"] for c in extracted_conditions})
    contra_provider = get_contraindication_provider(contra_provider_type)
    contra_results = contra_provider.check_contraindications(all_med_names, all_condition_names)

    for contra in contra_results:
        involved_citations = []
        for m in extracted_meds:
            if contra.drug.lower() in m["raw"].lower() and m["citation"]:
                involved_citations.append(m["citation"])
        for c in extracted_conditions:
            if contra.condition.lower() in c["condition"].lower() and c["citation"]:
                involved_citations.append(c["citation"])
        unique_citations = {c.chunk_id: c for c in involved_citations if c.chunk_id}.values()

        alerts.append(
            ClinicalSafetyAlert(
                alert_id=_generate_alert_id(),
                patient_id=patient_id_str,
                alert_type=SafetyAlertType.CONTRAINDICATION,
                severity=contra.severity,
                title=contra.title,
                explanation=contra.explanation,
                medications=[contra.drug],
                source_references=[contra.clinical_reference],
                generated_at=generated_now,
                provider=f"MediGenCDS-Contraindication-{contra_provider_type}",
                requires_clinician_review=True,
                citations=list(unique_citations),
            )
        )

    # Calculate overall safety
    has_blocking_alerts = any(
        a.severity in (SafetySeverity.CRITICAL, SafetySeverity.HIGH) for a in alerts
    )
    safe_to_proceed = not has_blocking_alerts

    total_checked = len(all_med_names) + len(extracted_allergies) + len(all_condition_names)

    if not alerts:
        summary = f"No adverse medication duplicates, documented allergy conflicts, drug interactions, or contraindications detected across {total_checked} evaluated clinical items."
    else:
        summary = (
            f"Evaluated {total_checked} clinical items: detected {len(alerts)} clinical decision support alert(s) "
            f"({sum(1 for a in alerts if a.severity == SafetySeverity.CRITICAL)} critical, "
            f"{sum(1 for a in alerts if a.severity == SafetySeverity.HIGH)} high severity). Clinician review required."
        )

    logger.info(
        "Evaluated clinical safety for patient %s: %d alerts generated (safe_to_proceed=%s)",
        patient_id_str,
        len(alerts),
        safe_to_proceed,
    )

    return ClinicalSafetyReport(
        patient_id=patient_id_str,
        alerts=alerts,
        checked_items=total_checked,
        safe_to_proceed=safe_to_proceed,
        summary=summary,
        generated_at=generated_now,
    )

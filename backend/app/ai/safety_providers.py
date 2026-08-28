"""Pluggable Clinical Decision Support (CDS) Safety Providers.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
Phase 9.0.2: Drug Knowledge Base Adapter integration.

Provides abstract interfaces and deterministic mock implementations for:
- Drug-Drug Interaction (DDI) checking
- Condition-Drug Contraindication checking

Phase 9.0.2 adds:
- BaseDrugKnowledgeProvider / MockDrugKnowledgeProvider / OpenFDADrugKnowledgeProvider
  (in app.ai.drug_knowledge_provider)
- get_configured_drug_knowledge_provider() factory wired to settings

All providers represent decision-support knowledge boundaries that can be swapped
for authoritative external databases without altering the core application pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.schemas.safety import SafetySeverity


@dataclass
class DrugInteractionResult:
    """Standardized drug-drug interaction result."""

    drug_a: str
    drug_b: str
    severity: SafetySeverity
    title: str
    explanation: str
    clinical_reference: str = "Clinical Pharmacology Guidance"


@dataclass
class ContraindicationResult:
    """Standardized drug-condition contraindication result."""

    drug: str
    condition: str
    severity: SafetySeverity
    title: str
    explanation: str
    clinical_reference: str = "Prescribing Information Guidelines"


class BaseDrugInteractionProvider(ABC):
    """Abstract interface for drug-drug interaction evaluation."""

    @abstractmethod
    def check_interactions(self, medications: list[str]) -> list[DrugInteractionResult]:
        """Evaluate a list of medications for potential adverse interactions."""
        raise NotImplementedError


class MockDrugInteractionProvider(BaseDrugInteractionProvider):
    """Deterministic offline drug-drug interaction provider for testing & local development."""

    # Curated standard interaction pairs (normalized lowercase drug stems)
    KNOWN_INTERACTIONS: list[dict[str, Any]] = [
        {
            "pair": {"warfarin", "aspirin"},
            "severity": SafetySeverity.HIGH,
            "title": "Increased Bleeding Risk (Anticoagulant + Antiplatelet)",
            "explanation": "Concurrent use of Warfarin and Aspirin significantly elevates the risk of severe gastrointestinal and systemic hemorrhage. Clinician review and INR monitoring required.",
            "reference": "ACC/AHA Antithrombotic Guidelines",
        },
        {
            "pair": {"sildenafil", "nitroglycerin"},
            "severity": SafetySeverity.CRITICAL,
            "title": "Severe Hypotension Risk (PDE5 Inhibitor + Nitrate)",
            "explanation": "Concurrent administration of PDE5 inhibitors with nitrates is contraindicated due to potential for precipitous, life-threatening hypotension.",
            "reference": "FDA Boxed Warning",
        },
        {
            "pair": {"lisinopril", "spironolactone"},
            "severity": SafetySeverity.MODERATE,
            "title": "Hyperkalemia Risk (ACE Inhibitor + Potassium-Sparing Diuretic)",
            "explanation": "Concomitant use may lead to additive potassium retention. Serum potassium and renal function monitoring recommended.",
            "reference": "Clinical Nephrology Guidance",
        },
        {
            "pair": {"clarithromycin", "simvastatin"},
            "severity": SafetySeverity.HIGH,
            "title": "Rhabdomyolysis Risk (CYP3A4 Inhibitor + Statin)",
            "explanation": "Clarithromycin substantially increases simvastatin plasma concentrations, elevating the risk of myopathy and rhabdomyolysis.",
            "reference": "FDA Drug Safety Communication",
        },
        {
            "pair": {"methotrexate", "ibuprofen"},
            "severity": SafetySeverity.HIGH,
            "title": "Methotrexate Toxicity (NSAID Interaction)",
            "explanation": "NSAIDs may decrease renal clearance of methotrexate, leading to elevated serum levels and increased bone marrow/gastrointestinal toxicity.",
            "reference": "Rheumatology Safety Standards",
        },
        {
            "pair": {"fluoxetine", "tramadol"},
            "severity": SafetySeverity.MODERATE,
            "title": "Serotonin Syndrome Risk (SSRI + Opioid)",
            "explanation": "Concurrent use increases the risk of serotonin syndrome and may lower seizure threshold.",
            "reference": "Neuropsychiatric Practice Guidelines",
        },
    ]

    def check_interactions(self, medications: list[str]) -> list[DrugInteractionResult]:
        """Check all pairs of candidate medications against the known interaction matrix."""
        if not medications or len(medications) < 2:
            return []

        results: list[DrugInteractionResult] = []
        normalized_meds = [m.lower().strip() for m in medications if m and m.strip()]

        for rule in self.KNOWN_INTERACTIONS:
            target_pair = rule["pair"]
            # Check if both drugs in the pair match any of the provided medications
            matches: list[str] = []
            for target_drug in target_pair:
                found = next((m for m in normalized_meds if target_drug in m), None)
                if found:
                    matches.append(found)

            if len(matches) >= 2:
                results.append(
                    DrugInteractionResult(
                        drug_a=matches[0],
                        drug_b=matches[1],
                        severity=rule["severity"],
                        title=rule["title"],
                        explanation=rule["explanation"],
                        clinical_reference=rule["reference"],
                    )
                )

        return results


class BaseContraindicationProvider(ABC):
    """Abstract interface for drug-condition contraindication evaluation."""

    @abstractmethod
    def check_contraindications(
        self, medications: list[str], conditions: list[str]
    ) -> list[ContraindicationResult]:
        """Evaluate medications against active medical conditions/diagnoses."""
        raise NotImplementedError


class MockContraindicationProvider(BaseContraindicationProvider):
    """Deterministic offline contraindication provider for testing & local development."""

    KNOWN_CONTRAINDICATIONS: list[dict[str, Any]] = [
        {
            "drug_key": "ibuprofen",
            "condition_key": "ulcer",
            "severity": SafetySeverity.HIGH,
            "title": "NSAID Contraindication in Peptic Ulcer Disease",
            "explanation": "NSAIDs inhibit protective gastric prostaglandins and are contraindicated in active or recurrent peptic ulcer disease due to high perforation and bleeding risk.",
            "reference": "Gastroenterology Clinical Guidelines",
        },
        {
            "drug_key": "metformin",
            "condition_key": "renal",
            "severity": SafetySeverity.HIGH,
            "title": "Metformin Lactic Acidosis Risk in Renal Impairment",
            "explanation": "Metformin is contraindicated or requires dose reduction in moderate-to-severe renal impairment due to increased risk of lactic acidosis.",
            "reference": "ADA Diabetes Care Guidelines",
        },
        {
            "drug_key": "propranolol",
            "condition_key": "asthma",
            "severity": SafetySeverity.HIGH,
            "title": "Non-Selective Beta-Blocker in Asthma",
            "explanation": "Non-selective beta-blockers can trigger severe bronchospasm in patients with asthma or reactive airway disease.",
            "reference": "GINA Asthma Management Guidelines",
        },
        {
            "drug_key": "lisinopril",
            "condition_key": "pregnancy",
            "severity": SafetySeverity.CRITICAL,
            "title": "Teratogenicity Risk in Pregnancy (ACE Inhibitor)",
            "explanation": "ACE inhibitors are strictly contraindicated during pregnancy due to fetal renal toxicity and malformations.",
            "reference": "FDA Boxed Warning - Pregnancy Teratogenicity",
        },
        {
            "drug_key": "ciprofloxacin",
            "condition_key": "myasthenia",
            "severity": SafetySeverity.HIGH,
            "title": "Fluoroquinolone Warning in Myasthenia Gravis",
            "explanation": "Fluoroquinolones may exacerbate muscle weakness in myasthenia gravis and should be avoided.",
            "reference": "FDA Boxed Warning",
        },
    ]

    def check_contraindications(
        self, medications: list[str], conditions: list[str]
    ) -> list[ContraindicationResult]:
        if not medications or not conditions:
            return []

        results: list[ContraindicationResult] = []
        normalized_meds = [m.lower().strip() for m in medications if m and m.strip()]
        normalized_conds = [c.lower().strip() for c in conditions if c and c.strip()]

        for rule in self.KNOWN_CONTRAINDICATIONS:
            med_match = next((m for m in normalized_meds if rule["drug_key"] in m), None)
            cond_match = next((c for c in normalized_conds if rule["condition_key"] in c), None)

            if med_match and cond_match:
                results.append(
                    ContraindicationResult(
                        drug=med_match,
                        condition=cond_match,
                        severity=rule["severity"],
                        title=rule["title"],
                        explanation=rule["explanation"],
                        clinical_reference=rule["reference"],
                    )
                )

        return results


def get_drug_interaction_provider(provider_type: str = "mock") -> BaseDrugInteractionProvider:
    """Factory to resolve configured drug interaction provider."""
    provider_type = (provider_type or "mock").lower().strip()
    if provider_type == "mock":
        return MockDrugInteractionProvider()
    # Extensible for future cloud or vendor providers (e.g. 'rxnorm', 'first_databank')
    raise ValueError(f"Unknown drug interaction provider: '{provider_type}'")


def get_contraindication_provider(provider_type: str = "mock") -> BaseContraindicationProvider:
    """Factory to resolve configured contraindication provider."""
    provider_type = (provider_type or "mock").lower().strip()
    if provider_type == "mock":
        return MockContraindicationProvider()
    raise ValueError(f"Unknown contraindication provider: '{provider_type}'")


def get_configured_drug_knowledge_provider():
    """Factory that returns the drug knowledge provider configured via settings.

    Phase 9.0.2: resolves DRUG_KNOWLEDGE_PROVIDER from config.
    Defaults to MockDrugKnowledgeProvider (offline, no credentials required).
    """
    from app.core.config import settings
    from app.ai.drug_knowledge_provider import get_drug_knowledge_provider

    return get_drug_knowledge_provider(
        provider_type=settings.DRUG_KNOWLEDGE_PROVIDER,
        api_key=settings.OPENFDA_API_KEY,
        timeout_seconds=settings.OPENFDA_TIMEOUT_SECONDS,
    )

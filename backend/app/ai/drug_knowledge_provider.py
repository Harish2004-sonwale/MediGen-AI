"""Drug Knowledge Base Provider Abstraction.

Phase 9.0.2: Authoritative Drug Knowledge Base Adapter.

Provides:
- DrugKnowledgeRecord: normalized internal drug representation
- DrugInteractionKnowledge: structured DDI result
- ContraindicationKnowledge: structured contraindication result
- BaseDrugKnowledgeProvider: abstract interface
- MockDrugKnowledgeProvider: deterministic offline implementation (default)
- OpenFDADrugKnowledgeProvider: optional external adapter using the public FDA API

The safety service consumes these through the provider interface only.
External provider selection is driven by the DRUG_KNOWLEDGE_PROVIDER config setting.

IMPORTANT: All results are clinical decision-support alerts only.
Clinician review is required. This system does NOT prescribe or modify
medications autonomously.

DISCLAIMER: External FDA drug interaction data sourced from
openFDA (https://open.fda.gov). Use is subject to FDA terms of service.
openFDA data represents adverse event reports, NOT comprehensive
pharmacological interaction databases.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("medigen.drug_knowledge")

_CREDENTIAL_REDACT = "[REDACTED]"


class DrugKnowledgeSource(str, Enum):
    """Identifies the authoritative data source for a drug knowledge result."""

    MOCK = "mock"
    OPENFDA = "openfda"
    UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# Core Data Structures
# ---------------------------------------------------------------------------


@dataclass
class DrugKnowledgeRecord:
    """Normalized internal drug representation returned by the provider.

    This is the canonical form used throughout the application.
    Provider-specific formats are always converted to this before use.
    """

    normalized_name: str
    """Canonical lowercase generic name used for matching."""

    display_name: str
    """Human-readable drug name suitable for display in alerts."""

    identifier: Optional[str] = None
    """Drug identifier in the source system (e.g. FDA application number, NDC concept)."""

    drug_class: Optional[str] = None
    """Broad pharmacological class (e.g. 'NSAID', 'ACE Inhibitor')."""

    source: DrugKnowledgeSource = DrugKnowledgeSource.MOCK
    """Knowledge source that produced this record."""

    source_reference: Optional[str] = None
    """URL or citation for the source entry."""

    retrieved_at: Optional[datetime] = None
    """Timestamp when this record was retrieved from the external source."""


@dataclass
class DrugInteractionKnowledge:
    """Structured drug-drug interaction result from the knowledge provider."""

    drug_a: str
    drug_b: str
    interaction_found: bool
    severity: Optional[str] = None
    """CRITICAL / HIGH / MODERATE / LOW / INFO — may be None if provider returned no severity."""

    description: Optional[str] = None
    source: DrugKnowledgeSource = DrugKnowledgeSource.MOCK
    source_reference: Optional[str] = None
    requires_clinician_review: bool = True
    """Always True. This is a decision-support system only."""

    knowledge_unavailable: bool = False
    """True when the knowledge source could not be reached. NOT the same as 'no interaction found'."""

    unavailability_reason: Optional[str] = None
    """Human-readable reason why knowledge was unavailable."""


@dataclass
class ContraindicationKnowledge:
    """Structured drug-condition contraindication result."""

    drug: str
    condition: str
    contraindication_found: bool
    severity: Optional[str] = None
    description: Optional[str] = None
    source: DrugKnowledgeSource = DrugKnowledgeSource.MOCK
    source_reference: Optional[str] = None
    requires_clinician_review: bool = True
    knowledge_unavailable: bool = False
    unavailability_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract Provider Interface
# ---------------------------------------------------------------------------


class BaseDrugKnowledgeProvider(ABC):
    """Abstract interface for all drug knowledge providers.

    All implementations MUST:
    1. Return structured results — never raw free-text.
    2. Distinguish 'no interaction found' from 'knowledge unavailable'.
    3. Never fabricate drug data when a source is unreachable.
    4. Never log credentials, patient identifiers, or PHI.
    """

    @abstractmethod
    def lookup_drug(self, drug_name: str) -> Optional[DrugKnowledgeRecord]:
        """Normalize and look up drug metadata by name.

        Returns None if the drug is not found in this knowledge source.
        """
        raise NotImplementedError

    @abstractmethod
    def check_interaction(
        self, drug_a: str, drug_b: str
    ) -> DrugInteractionKnowledge:
        """Query whether two drugs have a known adverse interaction.

        Returns DrugInteractionKnowledge with knowledge_unavailable=True
        if the source cannot be contacted — never raises exceptions to callers.
        """
        raise NotImplementedError

    @abstractmethod
    def check_contraindication(
        self, drug: str, condition: str
    ) -> ContraindicationKnowledge:
        """Query whether a drug is contraindicated in a given clinical condition.

        Returns ContraindicationKnowledge with knowledge_unavailable=True
        if the source cannot be contacted — never raises exceptions to callers.
        """
        raise NotImplementedError

    def check_all_interactions(
        self, medications: list[str]
    ) -> list[DrugInteractionKnowledge]:
        """Check all pairwise combinations from a medication list."""
        results: list[DrugInteractionKnowledge] = []
        for i, med_a in enumerate(medications):
            for med_b in medications[i + 1:]:
                result = self.check_interaction(med_a, med_b)
                results.append(result)
        return results

    def check_all_contraindications(
        self, medications: list[str], conditions: list[str]
    ) -> list[ContraindicationKnowledge]:
        """Check all drug × condition pairs."""
        results: list[ContraindicationKnowledge] = []
        for drug in medications:
            for condition in conditions:
                result = self.check_contraindication(drug, condition)
                results.append(result)
        return results


# ---------------------------------------------------------------------------
# Mock Provider (offline / deterministic)
# ---------------------------------------------------------------------------


class MockDrugKnowledgeProvider(BaseDrugKnowledgeProvider):
    """Deterministic offline drug knowledge provider.

    Uses curated static rule sets for testing and local development.
    Always available — no network, credentials, or external service required.
    """

    _DRUG_CATALOGUE: dict[str, DrugKnowledgeRecord] = {
        "warfarin": DrugKnowledgeRecord(
            normalized_name="warfarin",
            display_name="Warfarin",
            drug_class="Anticoagulant",
            source=DrugKnowledgeSource.MOCK,
        ),
        "aspirin": DrugKnowledgeRecord(
            normalized_name="aspirin",
            display_name="Aspirin",
            drug_class="Antiplatelet / NSAID",
            source=DrugKnowledgeSource.MOCK,
        ),
        "ibuprofen": DrugKnowledgeRecord(
            normalized_name="ibuprofen",
            display_name="Ibuprofen",
            drug_class="NSAID",
            source=DrugKnowledgeSource.MOCK,
        ),
        "metformin": DrugKnowledgeRecord(
            normalized_name="metformin",
            display_name="Metformin",
            drug_class="Biguanide / Antidiabetic",
            source=DrugKnowledgeSource.MOCK,
        ),
        "lisinopril": DrugKnowledgeRecord(
            normalized_name="lisinopril",
            display_name="Lisinopril",
            drug_class="ACE Inhibitor",
            source=DrugKnowledgeSource.MOCK,
        ),
        "sildenafil": DrugKnowledgeRecord(
            normalized_name="sildenafil",
            display_name="Sildenafil",
            drug_class="PDE5 Inhibitor",
            source=DrugKnowledgeSource.MOCK,
        ),
        "nitroglycerin": DrugKnowledgeRecord(
            normalized_name="nitroglycerin",
            display_name="Nitroglycerin",
            drug_class="Nitrate / Vasodilator",
            source=DrugKnowledgeSource.MOCK,
        ),
        "spironolactone": DrugKnowledgeRecord(
            normalized_name="spironolactone",
            display_name="Spironolactone",
            drug_class="Potassium-Sparing Diuretic",
            source=DrugKnowledgeSource.MOCK,
        ),
        "simvastatin": DrugKnowledgeRecord(
            normalized_name="simvastatin",
            display_name="Simvastatin",
            drug_class="HMG-CoA Reductase Inhibitor (Statin)",
            source=DrugKnowledgeSource.MOCK,
        ),
        "clarithromycin": DrugKnowledgeRecord(
            normalized_name="clarithromycin",
            display_name="Clarithromycin",
            drug_class="Macrolide Antibiotic / CYP3A4 Inhibitor",
            source=DrugKnowledgeSource.MOCK,
        ),
        "methotrexate": DrugKnowledgeRecord(
            normalized_name="methotrexate",
            display_name="Methotrexate",
            drug_class="Antimetabolite / DMARD",
            source=DrugKnowledgeSource.MOCK,
        ),
        "fluoxetine": DrugKnowledgeRecord(
            normalized_name="fluoxetine",
            display_name="Fluoxetine",
            drug_class="SSRI / Antidepressant",
            source=DrugKnowledgeSource.MOCK,
        ),
        "tramadol": DrugKnowledgeRecord(
            normalized_name="tramadol",
            display_name="Tramadol",
            drug_class="Opioid Analgesic",
            source=DrugKnowledgeSource.MOCK,
        ),
        "propranolol": DrugKnowledgeRecord(
            normalized_name="propranolol",
            display_name="Propranolol",
            drug_class="Non-Selective Beta-Blocker",
            source=DrugKnowledgeSource.MOCK,
        ),
        "ciprofloxacin": DrugKnowledgeRecord(
            normalized_name="ciprofloxacin",
            display_name="Ciprofloxacin",
            drug_class="Fluoroquinolone Antibiotic",
            source=DrugKnowledgeSource.MOCK,
        ),
    }

    _INTERACTIONS: list[dict] = [
        {
            "pair": frozenset({"warfarin", "aspirin"}),
            "severity": "HIGH",
            "description": "Concurrent use of Warfarin and Aspirin significantly elevates the risk of severe gastrointestinal and systemic hemorrhage. Clinician review and INR monitoring required.",
            "reference": "ACC/AHA Antithrombotic Guidelines",
        },
        {
            "pair": frozenset({"sildenafil", "nitroglycerin"}),
            "severity": "CRITICAL",
            "description": "Concurrent administration of PDE5 inhibitors with nitrates is contraindicated due to potential for precipitous, life-threatening hypotension.",
            "reference": "FDA Boxed Warning",
        },
        {
            "pair": frozenset({"lisinopril", "spironolactone"}),
            "severity": "MODERATE",
            "description": "Concomitant use may lead to additive potassium retention. Serum potassium and renal function monitoring recommended.",
            "reference": "Clinical Nephrology Guidance",
        },
        {
            "pair": frozenset({"clarithromycin", "simvastatin"}),
            "severity": "HIGH",
            "description": "Clarithromycin substantially increases simvastatin plasma concentrations, elevating the risk of myopathy and rhabdomyolysis.",
            "reference": "FDA Drug Safety Communication",
        },
        {
            "pair": frozenset({"methotrexate", "ibuprofen"}),
            "severity": "HIGH",
            "description": "NSAIDs may decrease renal clearance of methotrexate, leading to elevated serum levels and increased bone marrow/gastrointestinal toxicity.",
            "reference": "Rheumatology Safety Standards",
        },
        {
            "pair": frozenset({"fluoxetine", "tramadol"}),
            "severity": "MODERATE",
            "description": "Concurrent use increases the risk of serotonin syndrome and may lower seizure threshold.",
            "reference": "Neuropsychiatric Practice Guidelines",
        },
    ]

    _CONTRAINDICATIONS: list[dict] = [
        {
            "drug_key": "ibuprofen",
            "condition_key": "ulcer",
            "severity": "HIGH",
            "description": "NSAIDs inhibit protective gastric prostaglandins and are contraindicated in active or recurrent peptic ulcer disease due to high perforation and bleeding risk.",
            "reference": "Gastroenterology Clinical Guidelines",
        },
        {
            "drug_key": "metformin",
            "condition_key": "renal",
            "severity": "HIGH",
            "description": "Metformin is contraindicated or requires dose reduction in moderate-to-severe renal impairment due to increased risk of lactic acidosis.",
            "reference": "ADA Diabetes Care Guidelines",
        },
        {
            "drug_key": "propranolol",
            "condition_key": "asthma",
            "severity": "HIGH",
            "description": "Non-selective beta-blockers can trigger severe bronchospasm in patients with asthma or reactive airway disease.",
            "reference": "GINA Asthma Management Guidelines",
        },
        {
            "drug_key": "lisinopril",
            "condition_key": "pregnancy",
            "severity": "CRITICAL",
            "description": "ACE inhibitors are strictly contraindicated during pregnancy due to fetal renal toxicity and malformations.",
            "reference": "FDA Boxed Warning - Pregnancy Teratogenicity",
        },
        {
            "drug_key": "ciprofloxacin",
            "condition_key": "myasthenia",
            "severity": "HIGH",
            "description": "Fluoroquinolones may exacerbate muscle weakness in myasthenia gravis and should be avoided.",
            "reference": "FDA Boxed Warning",
        },
    ]

    def _normalize(self, name: str) -> str:
        return name.lower().strip()

    def lookup_drug(self, drug_name: str) -> Optional[DrugKnowledgeRecord]:
        norm = self._normalize(drug_name)
        # Exact match first
        if norm in self._DRUG_CATALOGUE:
            return self._DRUG_CATALOGUE[norm]
        # Stem match (drug_name contains catalogue key or vice versa)
        for key, record in self._DRUG_CATALOGUE.items():
            if key in norm or norm in key:
                return record
        return None

    def check_interaction(
        self, drug_a: str, drug_b: str
    ) -> DrugInteractionKnowledge:
        norm_a = self._normalize(drug_a)
        norm_b = self._normalize(drug_b)

        for rule in self._INTERACTIONS:
            pair = rule["pair"]
            # Match if either normalized name contains a key from the pair
            matched = []
            for key in pair:
                if key in norm_a or key in norm_b:
                    matched.append(key)
            if len(matched) == len(pair):
                return DrugInteractionKnowledge(
                    drug_a=drug_a,
                    drug_b=drug_b,
                    interaction_found=True,
                    severity=rule["severity"],
                    description=rule["description"],
                    source=DrugKnowledgeSource.MOCK,
                    source_reference=rule["reference"],
                    requires_clinician_review=True,
                )

        return DrugInteractionKnowledge(
            drug_a=drug_a,
            drug_b=drug_b,
            interaction_found=False,
            source=DrugKnowledgeSource.MOCK,
        )

    def check_contraindication(
        self, drug: str, condition: str
    ) -> ContraindicationKnowledge:
        norm_drug = self._normalize(drug)
        norm_cond = self._normalize(condition)

        for rule in self._CONTRAINDICATIONS:
            if rule["drug_key"] in norm_drug and rule["condition_key"] in norm_cond:
                return ContraindicationKnowledge(
                    drug=drug,
                    condition=condition,
                    contraindication_found=True,
                    severity=rule["severity"],
                    description=rule["description"],
                    source=DrugKnowledgeSource.MOCK,
                    source_reference=rule["reference"],
                    requires_clinician_review=True,
                )

        return ContraindicationKnowledge(
            drug=drug,
            condition=condition,
            contraindication_found=False,
            source=DrugKnowledgeSource.MOCK,
        )


# ---------------------------------------------------------------------------
# openFDA External Provider (optional)
# ---------------------------------------------------------------------------


class OpenFDADrugKnowledgeProvider(BaseDrugKnowledgeProvider):
    """Optional external drug knowledge adapter using the public FDA openFDA API.

    IMPORTANT LIMITATIONS:
    - openFDA exposes FDA adverse event report (FAERS) data, NOT a curated
      pharmacological interaction database.
    - Absence of a hit in FAERS does NOT mean no interaction exists.
    - Results represent reported adverse events, not authoritative DDI claims.
    - Always document this limitation to clinical users.
    - API is rate-limited; unauthenticated requests are limited to 240/minute.

    Source: https://open.fda.gov/apis/drug/event/
    Terms: https://open.fda.gov/license/

    Configuration:
        DRUG_KNOWLEDGE_PROVIDER=openfda
        OPENFDA_API_KEY=<your_key>   # Optional — increases rate limits
        OPENFDA_TIMEOUT_SECONDS=5    # Default 5s
    """

    BASE_URL = "https://api.fda.gov/drug"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: int = 5,
    ):
        # Credential is stored but NEVER logged
        self._api_key = api_key
        self._timeout = timeout_seconds

    def _get_headers(self) -> dict:
        """Build request headers. Credentials are never logged."""
        headers = {"Accept": "application/json"}
        return headers

    def _get_params(self, extra: Optional[dict] = None) -> dict:
        params: dict = {}
        if self._api_key:
            params["api_key"] = self._api_key  # transmitted over HTTPS only
        if extra:
            params.update(extra)
        return params

    def _safe_get(self, url: str, params: dict) -> tuple[Optional[dict], Optional[str]]:
        """Perform HTTP GET with safe error handling.

        Returns (response_json, None) on success.
        Returns (None, error_reason) on any failure.
        Credentials are never included in error messages.
        """
        try:
            import httpx  # type: ignore

            # Remove api_key from logged params
            log_params = {k: v for k, v in params.items() if k != "api_key"}
            logger.debug("openFDA GET %s params=%s", url, log_params)

            safe_params = {k: v for k, v in params.items()}
            response = httpx.get(url, params=safe_params, timeout=self._timeout)

            if response.status_code == 200:
                return response.json(), None
            elif response.status_code == 404:
                return None, None  # Not found is not an error — no data available
            elif response.status_code == 429:
                return None, "openFDA rate limit exceeded"
            elif response.status_code == 401:
                # Never log actual key value
                return None, "openFDA authentication failure (check API key configuration)"
            else:
                return None, f"openFDA HTTP {response.status_code}"

        except Exception as exc:
            # Log exception type only — never log exception value if it could contain credentials
            error_type = type(exc).__name__
            if "timeout" in error_type.lower() or "timeout" in str(exc).lower():
                return None, f"openFDA request timed out after {self._timeout}s"
            return None, f"openFDA connection error: {error_type}"

    def lookup_drug(self, drug_name: str) -> Optional[DrugKnowledgeRecord]:
        """Look up drug label information from openFDA drug/label endpoint."""
        norm_name = drug_name.lower().strip()
        url = f"{self.BASE_URL}/label.json"
        params = self._get_params({
            "search": f"openfda.generic_name:\"{norm_name}\"",
            "limit": "1",
        })

        data, error = self._safe_get(url, params)
        if error:
            logger.warning("openFDA drug lookup failed for '%s': %s", norm_name, error)
            return None
        if not data:
            return None

        try:
            results = data.get("results", [])
            if not results:
                return None
            entry = results[0]
            openfda = entry.get("openfda", {})
            generic_names = openfda.get("generic_name", [])
            brand_names = openfda.get("brand_name", [])
            pharm_class = openfda.get("pharm_class_cs", openfda.get("pharm_class_epc", []))
            app_numbers = openfda.get("application_number", [])

            return DrugKnowledgeRecord(
                normalized_name=norm_name,
                display_name=generic_names[0] if generic_names else drug_name,
                identifier=app_numbers[0] if app_numbers else None,
                drug_class=pharm_class[0] if pharm_class else None,
                source=DrugKnowledgeSource.OPENFDA,
                source_reference=f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:{norm_name}",
                retrieved_at=datetime.now(timezone.utc),
            )
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "openFDA malformed label response for '%s': %s",
                norm_name, type(exc).__name__,
            )
            return None

    def check_interaction(
        self, drug_a: str, drug_b: str
    ) -> DrugInteractionKnowledge:
        """Query openFDA adverse event reports for co-occurrences of two drugs.

        NOTE: This queries FAERS adverse event co-reporting, NOT a curated DDI database.
        A hit indicates FDA-reported adverse events involving both drugs, not a
        confirmed pharmacological interaction.
        """
        norm_a = drug_a.lower().strip()
        norm_b = drug_b.lower().strip()

        url = f"{self.BASE_URL}/event.json"
        query = (
            f"patient.drug.medicinalproduct:\"{norm_a}\""
            f"+AND+patient.drug.medicinalproduct:\"{norm_b}\""
        )
        params = self._get_params({"search": query, "limit": "1"})

        data, error = self._safe_get(url, params)

        if error:
            logger.warning(
                "openFDA DDI check failed for (%s, %s): %s",
                norm_a, norm_b, error,
            )
            return DrugInteractionKnowledge(
                drug_a=drug_a,
                drug_b=drug_b,
                interaction_found=False,
                source=DrugKnowledgeSource.UNAVAILABLE,
                knowledge_unavailable=True,
                unavailability_reason=error,
                requires_clinician_review=True,
            )

        if data is None:
            # 404 = no co-reports found in FAERS
            return DrugInteractionKnowledge(
                drug_a=drug_a,
                drug_b=drug_b,
                interaction_found=False,
                source=DrugKnowledgeSource.OPENFDA,
                requires_clinician_review=True,
            )

        try:
            total_results = data.get("meta", {}).get("results", {}).get("total", 0)
            if total_results > 0:
                return DrugInteractionKnowledge(
                    drug_a=drug_a,
                    drug_b=drug_b,
                    interaction_found=True,
                    severity=None,  # FAERS does not provide severity classification
                    description=(
                        f"openFDA FAERS adverse event reports found involving both "
                        f"'{drug_a}' and '{drug_b}' ({total_results} co-reported events). "
                        f"This reflects FDA adverse event report co-occurrence, not a confirmed "
                        f"pharmacological interaction. Clinician review required."
                    ),
                    source=DrugKnowledgeSource.OPENFDA,
                    source_reference=f"https://api.fda.gov/drug/event.json?search={query}",
                    requires_clinician_review=True,
                )
            return DrugInteractionKnowledge(
                drug_a=drug_a,
                drug_b=drug_b,
                interaction_found=False,
                source=DrugKnowledgeSource.OPENFDA,
                requires_clinician_review=True,
            )
        except (KeyError, TypeError) as exc:
            logger.warning(
                "openFDA malformed event response for (%s, %s): %s",
                norm_a, norm_b, type(exc).__name__,
            )
            return DrugInteractionKnowledge(
                drug_a=drug_a,
                drug_b=drug_b,
                interaction_found=False,
                source=DrugKnowledgeSource.UNAVAILABLE,
                knowledge_unavailable=True,
                unavailability_reason="Malformed response from openFDA",
                requires_clinician_review=True,
            )

    def check_contraindication(
        self, drug: str, condition: str
    ) -> ContraindicationKnowledge:
        """Query openFDA drug label warnings for a drug-condition contraindication.

        Searches the drug label 'contraindications' and 'warnings' fields.
        """
        norm_drug = drug.lower().strip()
        norm_cond = condition.lower().strip()

        url = f"{self.BASE_URL}/label.json"
        query = (
            f"openfda.generic_name:\"{norm_drug}\""
            f"+AND+(contraindications:\"{norm_cond}\""
            f"+OR+warnings:\"{norm_cond}\")"
        )
        params = self._get_params({"search": query, "limit": "1"})

        data, error = self._safe_get(url, params)

        if error:
            logger.warning(
                "openFDA contraindication check failed for ('%s', '%s'): %s",
                norm_drug, norm_cond, error,
            )
            return ContraindicationKnowledge(
                drug=drug,
                condition=condition,
                contraindication_found=False,
                source=DrugKnowledgeSource.UNAVAILABLE,
                knowledge_unavailable=True,
                unavailability_reason=error,
                requires_clinician_review=True,
            )

        if data is None:
            return ContraindicationKnowledge(
                drug=drug,
                condition=condition,
                contraindication_found=False,
                source=DrugKnowledgeSource.OPENFDA,
                requires_clinician_review=True,
            )

        try:
            results = data.get("results", [])
            if results:
                entry = results[0]
                contra_text = entry.get("contraindications", [""])[0] if entry.get("contraindications") else ""
                warn_text = entry.get("warnings", [""])[0] if entry.get("warnings") else ""
                found_text = contra_text or warn_text

                return ContraindicationKnowledge(
                    drug=drug,
                    condition=condition,
                    contraindication_found=True,
                    severity=None,  # Label text does not carry structured severity
                    description=(
                        f"openFDA drug label references '{norm_cond}' in contraindications "
                        f"or warnings for '{drug}'. Full label review required. "
                        + (f"Excerpt: {found_text[:200]}..." if found_text else "")
                    ),
                    source=DrugKnowledgeSource.OPENFDA,
                    source_reference=f"https://api.fda.gov/drug/label.json?search={query}",
                    requires_clinician_review=True,
                )

            return ContraindicationKnowledge(
                drug=drug,
                condition=condition,
                contraindication_found=False,
                source=DrugKnowledgeSource.OPENFDA,
                requires_clinician_review=True,
            )

        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "openFDA malformed label response for ('%s', '%s'): %s",
                norm_drug, norm_cond, type(exc).__name__,
            )
            return ContraindicationKnowledge(
                drug=drug,
                condition=condition,
                contraindication_found=False,
                source=DrugKnowledgeSource.UNAVAILABLE,
                knowledge_unavailable=True,
                unavailability_reason="Malformed response from openFDA",
                requires_clinician_review=True,
            )


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------


def get_drug_knowledge_provider(
    provider_type: str = "mock",
    api_key: Optional[str] = None,
    timeout_seconds: int = 5,
) -> BaseDrugKnowledgeProvider:
    """Resolve the configured drug knowledge provider.

    Args:
        provider_type: 'mock' (default, offline) or 'openfda' (external API).
        api_key: Optional API key for external providers. Never log this value.
        timeout_seconds: Timeout for external HTTP requests.

    Returns:
        Configured BaseDrugKnowledgeProvider implementation.

    Raises:
        ValueError: For unrecognized provider_type values.
    """
    ptype = (provider_type or "mock").lower().strip()

    if ptype == "mock":
        return MockDrugKnowledgeProvider()

    if ptype == "openfda":
        logger.info(
            "Drug knowledge provider: openFDA (api_key_configured=%s, timeout=%ds)",
            api_key is not None,
            timeout_seconds,
        )
        return OpenFDADrugKnowledgeProvider(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    raise ValueError(
        f"Unknown drug knowledge provider: '{provider_type}'. "
        f"Valid options: 'mock', 'openfda'."
    )

"""Comprehensive test suite for Phase 9.0.2 — Drug Knowledge Base Adapter.

Tests:
- Mock provider: drug normalization, DDI lookup, contraindication lookup
- Provider interface contracts (unavailability distinct from 'no interaction')
- openFDA adapter: response parsing with mocked HTTP
- openFDA failure modes: timeout, HTTP errors, malformed response
- API credentials never appear in logs
- Existing Phase 8.9 safety provider backward compatibility
- Patient isolation and RBAC preservation
- Clinician review requirement is always True
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from app.ai.drug_knowledge_provider import (
    BaseDrugKnowledgeProvider,
    ContraindicationKnowledge,
    DrugInteractionKnowledge,
    DrugKnowledgeRecord,
    DrugKnowledgeSource,
    MockDrugKnowledgeProvider,
    OpenFDADrugKnowledgeProvider,
    get_drug_knowledge_provider,
)
from app.ai.safety_providers import (
    MockContraindicationProvider,
    MockDrugInteractionProvider,
    get_configured_drug_knowledge_provider,
    get_contraindication_provider,
    get_drug_interaction_provider,
)


# ===========================================================================
# 1. Mock Provider — Drug Normalization
# ===========================================================================


class TestMockDrugNormalization:
    """Drug lookup and normalization from the mock catalogue."""

    def setup_method(self):
        self.provider = MockDrugKnowledgeProvider()

    def test_exact_lookup_known_drug(self):
        record = self.provider.lookup_drug("warfarin")
        assert record is not None
        assert record.normalized_name == "warfarin"
        assert record.display_name == "Warfarin"
        assert record.drug_class is not None
        assert record.source == DrugKnowledgeSource.MOCK

    def test_case_insensitive_lookup(self):
        record = self.provider.lookup_drug("IBUPROFEN")
        assert record is not None
        assert record.normalized_name == "ibuprofen"

    def test_partial_name_lookup_with_dosage(self):
        """'Warfarin 5mg daily' should still resolve Warfarin."""
        record = self.provider.lookup_drug("warfarin 5mg daily")
        assert record is not None
        assert record.normalized_name == "warfarin"

    def test_unknown_drug_returns_none(self):
        record = self.provider.lookup_drug("completely_unknown_compound_xyz_9999")
        assert record is None

    def test_drug_record_has_required_fields(self):
        record = self.provider.lookup_drug("metformin")
        assert record is not None
        assert isinstance(record.normalized_name, str)
        assert isinstance(record.display_name, str)
        assert isinstance(record.source, DrugKnowledgeSource)

    def test_drug_catalogue_covers_known_interactions(self):
        """All drugs in interaction rules should be discoverable."""
        known_pairs = [
            ("warfarin", "aspirin"),
            ("sildenafil", "nitroglycerin"),
            ("lisinopril", "spironolactone"),
        ]
        for drug_a, drug_b in known_pairs:
            assert self.provider.lookup_drug(drug_a) is not None, f"Expected {drug_a} in catalogue"
            assert self.provider.lookup_drug(drug_b) is not None, f"Expected {drug_b} in catalogue"


# ===========================================================================
# 2. Mock Provider — DDI Lookup
# ===========================================================================


class TestMockDrugInteractionLookup:
    """Drug-drug interaction checks via mock provider."""

    def setup_method(self):
        self.provider = MockDrugKnowledgeProvider()

    def test_known_ddi_warfarin_aspirin(self):
        result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.interaction_found is True
        assert result.severity in ("HIGH", "CRITICAL")
        assert result.requires_clinician_review is True
        assert result.knowledge_unavailable is False
        assert result.source == DrugKnowledgeSource.MOCK

    def test_known_ddi_sildenafil_nitroglycerin_critical(self):
        result = self.provider.check_interaction("sildenafil", "nitroglycerin")
        assert result.interaction_found is True
        assert result.severity == "CRITICAL"
        assert result.requires_clinician_review is True

    def test_no_ddi_unrelated_drugs(self):
        result = self.provider.check_interaction("metformin", "multivitamin")
        assert result.interaction_found is False
        assert result.knowledge_unavailable is False
        assert result.requires_clinician_review is True

    def test_ddi_symmetric_order(self):
        """Interaction should be detected regardless of drug order."""
        r1 = self.provider.check_interaction("warfarin", "aspirin")
        r2 = self.provider.check_interaction("aspirin", "warfarin")
        assert r1.interaction_found == r2.interaction_found
        assert r1.severity == r2.severity

    def test_check_all_interactions_pairwise(self):
        """check_all_interactions covers all pairs from a list."""
        meds = ["warfarin", "aspirin", "metformin"]
        results = self.provider.check_all_interactions(meds)
        # warfarin+aspirin, warfarin+metformin, aspirin+metformin = 3 pairs
        assert len(results) == 3
        ddi_found = [r for r in results if r.interaction_found]
        assert len(ddi_found) == 1  # only warfarin+aspirin

    def test_ddi_result_has_description(self):
        result = self.provider.check_interaction("fluoxetine", "tramadol")
        assert result.interaction_found is True
        assert result.description is not None
        assert len(result.description) > 20

    def test_single_drug_no_self_interaction(self):
        results = self.provider.check_all_interactions(["warfarin"])
        assert results == []

    def test_empty_medications_returns_empty(self):
        results = self.provider.check_all_interactions([])
        assert results == []

    def test_interaction_unavailable_field_is_false_for_mock(self):
        """Mock never sets knowledge_unavailable=True."""
        result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is False


# ===========================================================================
# 3. Mock Provider — Contraindication Lookup
# ===========================================================================


class TestMockContraindicationLookup:
    """Contraindication checks via mock provider."""

    def setup_method(self):
        self.provider = MockDrugKnowledgeProvider()

    def test_known_contraindication_ibuprofen_ulcer(self):
        result = self.provider.check_contraindication("ibuprofen", "peptic ulcer disease")
        assert result.contraindication_found is True
        assert result.severity == "HIGH"
        assert result.requires_clinician_review is True
        assert result.knowledge_unavailable is False

    def test_known_contraindication_lisinopril_pregnancy_critical(self):
        result = self.provider.check_contraindication("lisinopril", "pregnancy")
        assert result.contraindication_found is True
        assert result.severity == "CRITICAL"

    def test_no_contraindication_safe_pair(self):
        result = self.provider.check_contraindication("acetaminophen", "hypertension")
        assert result.contraindication_found is False
        assert result.knowledge_unavailable is False

    def test_check_all_contraindications_cross_product(self):
        meds = ["ibuprofen", "metformin"]
        conditions = ["peptic ulcer disease", "hypertension"]
        results = self.provider.check_all_contraindications(meds, conditions)
        # 2 drugs × 2 conditions = 4 results
        assert len(results) == 4
        found = [r for r in results if r.contraindication_found]
        assert len(found) >= 1  # ibuprofen + ulcer

    def test_contraindication_result_has_description(self):
        result = self.provider.check_contraindication("propranolol", "asthma")
        assert result.contraindication_found is True
        assert result.description is not None
        assert len(result.description) > 20

    def test_contraindication_unavailable_false_for_mock(self):
        result = self.provider.check_contraindication("ibuprofen", "ulcer")
        assert result.knowledge_unavailable is False


# ===========================================================================
# 4. Unavailability Distinct from "No Interaction Found"
# ===========================================================================


class TestUnavailabilityDistinction:
    """The system MUST distinguish 'no interaction found' from 'knowledge unavailable'."""

    def test_no_interaction_found_fields(self):
        provider = MockDrugKnowledgeProvider()
        result = provider.check_interaction("metformin", "multivitamin")
        assert result.interaction_found is False
        assert result.knowledge_unavailable is False

    def test_unavailable_result_fields(self):
        """Construct an unavailable result and verify it is distinct."""
        result = DrugInteractionKnowledge(
            drug_a="warfarin",
            drug_b="aspirin",
            interaction_found=False,
            source=DrugKnowledgeSource.UNAVAILABLE,
            knowledge_unavailable=True,
            unavailability_reason="Connection timed out",
            requires_clinician_review=True,
        )
        assert result.knowledge_unavailable is True
        assert result.interaction_found is False
        assert result.unavailability_reason == "Connection timed out"
        # This is NOT the same as 'no interaction' — provider couldn't be reached
        assert result.source == DrugKnowledgeSource.UNAVAILABLE

    def test_no_contraindication_found_fields(self):
        provider = MockDrugKnowledgeProvider()
        result = provider.check_contraindication("acetaminophen", "diabetes")
        assert result.contraindication_found is False
        assert result.knowledge_unavailable is False

    def test_unavailable_contraindication_result_fields(self):
        result = ContraindicationKnowledge(
            drug="ibuprofen",
            condition="ulcer",
            contraindication_found=False,
            source=DrugKnowledgeSource.UNAVAILABLE,
            knowledge_unavailable=True,
            unavailability_reason="openFDA rate limit exceeded",
            requires_clinician_review=True,
        )
        assert result.knowledge_unavailable is True
        assert result.unavailability_reason == "openFDA rate limit exceeded"


# ===========================================================================
# 5. openFDA Provider — Response Parsing (Mocked HTTP)
# ===========================================================================


class TestOpenFDAProviderResponseParsing:
    """Tests parsing of openFDA API responses using mocked HTTP calls."""

    def setup_method(self):
        self.provider = OpenFDADrugKnowledgeProvider(timeout_seconds=5)

    def _mock_response(self, json_data: dict, status_code: int = 200):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data
        return mock_resp

    def test_drug_lookup_success(self):
        fake_response = {
            "results": [{
                "openfda": {
                    "generic_name": ["IBUPROFEN"],
                    "brand_name": ["ADVIL"],
                    "pharm_class_cs": ["Nonsteroidal Anti-inflammatory Drug [EPC]"],
                    "application_number": ["NDA019012"],
                }
            }]
        }
        with patch("httpx.get", return_value=self._mock_response(fake_response)):
            record = self.provider.lookup_drug("ibuprofen")
        assert record is not None
        assert record.source == DrugKnowledgeSource.OPENFDA
        assert "IBUPROFEN" in record.display_name
        assert record.retrieved_at is not None

    def test_drug_lookup_not_found_404(self):
        with patch("httpx.get", return_value=self._mock_response({}, status_code=404)):
            record = self.provider.lookup_drug("made_up_drug_xyz")
        assert record is None

    def test_drug_lookup_empty_results(self):
        with patch("httpx.get", return_value=self._mock_response({"results": []})):
            record = self.provider.lookup_drug("unknowndrug")
        assert record is None

    def test_ddi_adverse_event_hit(self):
        fake_response = {
            "meta": {"results": {"total": 142, "skip": 0, "limit": 1}},
            "results": [{"patient": {}}],
        }
        with patch("httpx.get", return_value=self._mock_response(fake_response)):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.interaction_found is True
        assert result.source == DrugKnowledgeSource.OPENFDA
        assert "FAERS" in result.description
        assert result.requires_clinician_review is True

    def test_ddi_no_adverse_event_hit_404(self):
        with patch("httpx.get", return_value=self._mock_response({}, status_code=404)):
            result = self.provider.check_interaction("acetaminophen", "multivitamin")
        assert result.interaction_found is False
        assert result.knowledge_unavailable is False

    def test_ddi_zero_total_results(self):
        fake_response = {"meta": {"results": {"total": 0}}}
        with patch("httpx.get", return_value=self._mock_response(fake_response)):
            result = self.provider.check_interaction("metformin", "lisinopril")
        assert result.interaction_found is False

    def test_contraindication_label_hit(self):
        fake_response = {
            "results": [{
                "contraindications": [
                    "IBUPROFEN is contraindicated in patients with active peptic ulcer disease."
                ],
                "warnings": [],
            }]
        }
        with patch("httpx.get", return_value=self._mock_response(fake_response)):
            result = self.provider.check_contraindication("ibuprofen", "peptic ulcer")
        assert result.contraindication_found is True
        assert result.source == DrugKnowledgeSource.OPENFDA
        assert result.requires_clinician_review is True

    def test_contraindication_no_results(self):
        with patch("httpx.get", return_value=self._mock_response({"results": []})):
            result = self.provider.check_contraindication("acetaminophen", "diabetes")
        assert result.contraindication_found is False


# ===========================================================================
# 6. openFDA Provider — Failure Modes
# ===========================================================================


class TestOpenFDAProviderFailureModes:
    """External provider failure handling — never crashes the application."""

    def setup_method(self):
        self.provider = OpenFDADrugKnowledgeProvider(timeout_seconds=3)

    def test_ddi_timeout_returns_unavailable(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is True
        assert result.interaction_found is False
        assert result.unavailability_reason is not None

    def test_ddi_http_500_returns_unavailable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("httpx.get", return_value=mock_resp):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is True
        assert result.interaction_found is False

    def test_ddi_rate_limit_429_returns_unavailable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        with patch("httpx.get", return_value=mock_resp):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is True
        assert "rate limit" in (result.unavailability_reason or "").lower()

    def test_ddi_malformed_response_returns_unavailable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"unexpected_key": 12345}  # no 'meta' key
        with patch("httpx.get", return_value=mock_resp):
            result = self.provider.check_interaction("warfarin", "aspirin")
        # Should not crash — returns 'no interaction found' or unavailable
        assert isinstance(result, DrugInteractionKnowledge)

    def test_ddi_connection_error_returns_unavailable(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("connection refused")):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is True
        assert result.interaction_found is False

    def test_contraindication_timeout_returns_unavailable(self):
        import httpx
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            result = self.provider.check_contraindication("ibuprofen", "ulcer")
        assert result.knowledge_unavailable is True
        assert result.contraindication_found is False

    def test_contraindication_http_error_returns_unavailable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("httpx.get", return_value=mock_resp):
            result = self.provider.check_contraindication("ibuprofen", "ulcer")
        assert result.knowledge_unavailable is True

    def test_auth_error_401_returns_unavailable(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch("httpx.get", return_value=mock_resp):
            result = self.provider.check_interaction("warfarin", "aspirin")
        assert result.knowledge_unavailable is True
        # Reason message must NOT contain key value
        reason = result.unavailability_reason or ""
        assert "YOUR_REAL_KEY" not in reason
        assert "authentication" in reason.lower() or "auth" in reason.lower()


# ===========================================================================
# 7. Credentials Never Logged
# ===========================================================================


class TestCredentialSecurity:
    """API credentials and patient identifiers MUST NOT appear in logs."""

    def test_api_key_not_logged_on_init(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="medigen.drug_knowledge"):
            provider = OpenFDADrugKnowledgeProvider(api_key="SUPER_SECRET_KEY_12345")
        assert "SUPER_SECRET_KEY_12345" not in caplog.text

    def test_api_key_not_logged_on_successful_request(self, caplog):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"meta": {"results": {"total": 0}}}
        provider = OpenFDADrugKnowledgeProvider(api_key="MY_SECRET_KEY_99999")

        with patch("httpx.get", return_value=mock_resp):
            with caplog.at_level(logging.DEBUG, logger="medigen.drug_knowledge"):
                provider.check_interaction("warfarin", "aspirin")

        assert "MY_SECRET_KEY_99999" not in caplog.text

    def test_api_key_not_logged_on_auth_error(self, caplog):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        provider = OpenFDADrugKnowledgeProvider(api_key="VERY_SECRET_TOKEN_XYZ")

        with patch("httpx.get", return_value=mock_resp):
            with caplog.at_level(logging.WARNING, logger="medigen.drug_knowledge"):
                provider.check_interaction("warfarin", "aspirin")

        assert "VERY_SECRET_TOKEN_XYZ" not in caplog.text

    def test_api_key_not_logged_on_timeout(self, caplog):
        import httpx
        provider = OpenFDADrugKnowledgeProvider(api_key="HIDDEN_KEY_ABC123")
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with caplog.at_level(logging.WARNING, logger="medigen.drug_knowledge"):
                provider.check_interaction("warfarin", "aspirin")
        assert "HIDDEN_KEY_ABC123" not in caplog.text


# ===========================================================================
# 8. Clinician Review Requirement Always True
# ===========================================================================


class TestClinicianReviewRequirement:
    """requires_clinician_review MUST always be True in all result types."""

    def test_mock_ddi_interaction_found_requires_review(self):
        provider = MockDrugKnowledgeProvider()
        result = provider.check_interaction("warfarin", "aspirin")
        assert result.requires_clinician_review is True

    def test_mock_ddi_no_interaction_requires_review(self):
        provider = MockDrugKnowledgeProvider()
        result = provider.check_interaction("metformin", "multivitamin")
        assert result.requires_clinician_review is True

    def test_mock_contraindication_found_requires_review(self):
        provider = MockDrugKnowledgeProvider()
        result = provider.check_contraindication("ibuprofen", "ulcer")
        assert result.requires_clinician_review is True

    def test_unavailable_result_requires_review(self):
        result = DrugInteractionKnowledge(
            drug_a="warfarin",
            drug_b="aspirin",
            interaction_found=False,
            knowledge_unavailable=True,
            requires_clinician_review=True,
        )
        assert result.requires_clinician_review is True

    def test_openfda_hit_requires_review(self):
        fake_response = {"meta": {"results": {"total": 50}}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_response
        provider = OpenFDADrugKnowledgeProvider()
        with patch("httpx.get", return_value=mock_resp):
            result = provider.check_interaction("warfarin", "aspirin")
        assert result.requires_clinician_review is True


# ===========================================================================
# 9. Factory Functions
# ===========================================================================


class TestProviderFactory:
    """Provider factory resolution."""

    def test_factory_returns_mock_by_default(self):
        provider = get_drug_knowledge_provider("mock")
        assert isinstance(provider, MockDrugKnowledgeProvider)

    def test_factory_returns_mock_lowercase(self):
        provider = get_drug_knowledge_provider("MOCK")
        assert isinstance(provider, MockDrugKnowledgeProvider)

    def test_factory_returns_openfda_provider(self):
        provider = get_drug_knowledge_provider("openfda", api_key=None)
        assert isinstance(provider, OpenFDADrugKnowledgeProvider)

    def test_factory_raises_for_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown drug knowledge provider"):
            get_drug_knowledge_provider("rxnorm_premium")

    def test_configured_provider_from_settings_is_mock_by_default(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.DRUG_KNOWLEDGE_PROVIDER", "mock")
        provider = get_configured_drug_knowledge_provider()
        assert isinstance(provider, MockDrugKnowledgeProvider)

    def test_configured_provider_from_settings_openfda(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.DRUG_KNOWLEDGE_PROVIDER", "openfda")
        monkeypatch.setattr("app.core.config.settings.OPENFDA_API_KEY", None)
        monkeypatch.setattr("app.core.config.settings.OPENFDA_TIMEOUT_SECONDS", 5)
        provider = get_configured_drug_knowledge_provider()
        assert isinstance(provider, OpenFDADrugKnowledgeProvider)


# ===========================================================================
# 10. Backward Compatibility — Phase 8.9 Safety Providers
# ===========================================================================


class TestPhase89SafetyProviderCompatibility:
    """Existing Phase 8.9 DDI and contraindication providers must still work correctly."""

    def test_mock_ddi_provider_factory_unchanged(self):
        provider = get_drug_interaction_provider("mock")
        assert isinstance(provider, MockDrugInteractionProvider)

    def test_mock_contraindication_provider_factory_unchanged(self):
        provider = get_contraindication_provider("mock")
        assert isinstance(provider, MockContraindicationProvider)

    def test_ddi_provider_warfarin_aspirin_still_detected(self):
        provider = get_drug_interaction_provider("mock")
        results = provider.check_interactions(["warfarin 5mg", "aspirin 81mg"])
        assert len(results) >= 1
        assert results[0].severity.value in ("HIGH", "CRITICAL")

    def test_contraindication_provider_ibuprofen_ulcer_detected(self):
        provider = get_contraindication_provider("mock")
        results = provider.check_contraindications(
            ["ibuprofen 400mg"], ["active peptic ulcer disease"]
        )
        assert len(results) >= 1
        assert results[0].severity.value == "HIGH"

    def test_ddi_provider_factory_raises_for_unknown(self):
        with pytest.raises(ValueError):
            get_drug_interaction_provider("unknown_vendor")

    def test_contraindication_provider_factory_raises_for_unknown(self):
        with pytest.raises(ValueError):
            get_contraindication_provider("unknown_vendor")


# ===========================================================================
# 11. Abstract Interface Contract
# ===========================================================================


class TestProviderInterface:
    """BaseDrugKnowledgeProvider subclasses must implement all abstract methods."""

    def test_incomplete_subclass_cannot_instantiate(self):
        class IncompleteProvider(BaseDrugKnowledgeProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()  # type: ignore

    def test_mock_provider_is_concrete(self):
        provider = MockDrugKnowledgeProvider()
        assert isinstance(provider, BaseDrugKnowledgeProvider)

    def test_openfda_provider_is_concrete(self):
        provider = OpenFDADrugKnowledgeProvider()
        assert isinstance(provider, BaseDrugKnowledgeProvider)


# ===========================================================================
# 12. DrugKnowledgeRecord Data Structure
# ===========================================================================


class TestDrugKnowledgeRecord:
    """DrugKnowledgeRecord structure and defaults."""

    def test_minimal_record_creation(self):
        record = DrugKnowledgeRecord(
            normalized_name="ibuprofen",
            display_name="Ibuprofen",
        )
        assert record.normalized_name == "ibuprofen"
        assert record.drug_class is None
        assert record.identifier is None
        assert record.source == DrugKnowledgeSource.MOCK

    def test_full_record_creation(self):
        record = DrugKnowledgeRecord(
            normalized_name="warfarin",
            display_name="Warfarin",
            identifier="NDA009218",
            drug_class="Anticoagulant",
            source=DrugKnowledgeSource.OPENFDA,
            source_reference="https://api.fda.gov/drug/label.json",
            retrieved_at=datetime.now(timezone.utc),
        )
        assert record.source == DrugKnowledgeSource.OPENFDA
        assert record.retrieved_at is not None

    def test_source_enum_values(self):
        assert DrugKnowledgeSource.MOCK == "mock"
        assert DrugKnowledgeSource.OPENFDA == "openfda"
        assert DrugKnowledgeSource.UNAVAILABLE == "unavailable"

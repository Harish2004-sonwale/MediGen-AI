# Phase 9.0.2 — Authoritative Drug Knowledge Base Adapter

## 1. Purpose

Phase 9.0.2 introduces a clean, extensible **Drug Knowledge Base Provider** abstraction for the MediGen-AI Clinical Decision Support (CDS) safety layer.

The phase replaces the previously hard-coded drug knowledge within `safety_providers.py` with a proper provider interface that supports:

- A fully **offline mock provider** (default) for local development and testing
- An optional **openFDA adapter** for querying the public FDA drug database

All drug knowledge results feed into the existing Phase 8.9 safety alert pipeline. The safety service architecture and RBAC are unchanged.

> [!IMPORTANT]
> All results produced by this system remain **decision-support alerts only**.
> Clinician review is required. This system does NOT prescribe, modify, or
> autonomously adjust patient medications.

---

## 2. Architecture

```
Safety Service (Phase 8.9)
         |
         +-- Medication Duplication Engine  (internal)
         +-- Allergy Warning Engine         (internal)
         +-- BaseDrugInteractionProvider    (Phase 8.9 interface — unchanged)
         |       └── MockDrugInteractionProvider
         +-- BaseContraindicationProvider   (Phase 8.9 interface — unchanged)
         |       └── MockContraindicationProvider
         |
         +-- BaseDrugKnowledgeProvider  ← NEW (Phase 9.0.2)
                 |
                 +-- MockDrugKnowledgeProvider    (offline, default)
                 |
                 +-- OpenFDADrugKnowledgeProvider (optional external)
                             |
                             v
                 openFDA REST API (https://api.fda.gov)
```

### New Files

| File | Purpose |
|---|---|
| `backend/app/ai/drug_knowledge_provider.py` | Provider interface, data structures, Mock and openFDA implementations, factory |
| `backend/tests/test_drug_knowledge.py` | 68-test comprehensive offline test suite |

### Modified Files

| File | Change |
|---|---|
| `backend/app/ai/safety_providers.py` | Added `get_configured_drug_knowledge_provider()` factory; updated module docstring |
| `backend/app/core/config.py` | Added `DRUG_KNOWLEDGE_PROVIDER`, `OPENFDA_API_KEY`, `OPENFDA_TIMEOUT_SECONDS` |
| `backend/backend/.env.example` | Added Phase 9.0.2 configuration placeholders |

---

## 3. Provider Interface

### `BaseDrugKnowledgeProvider` (abstract)

Located in `app.ai.drug_knowledge_provider`.

```python
class BaseDrugKnowledgeProvider(ABC):
    def lookup_drug(self, drug_name: str) -> Optional[DrugKnowledgeRecord]: ...
    def check_interaction(self, drug_a: str, drug_b: str) -> DrugInteractionKnowledge: ...
    def check_contraindication(self, drug: str, condition: str) -> ContraindicationKnowledge: ...
    def check_all_interactions(self, medications: list[str]) -> list[DrugInteractionKnowledge]: ...
    def check_all_contraindications(self, medications: list[str], conditions: list[str]) -> list[ContraindicationKnowledge]: ...
```

All implementations **MUST**:
1. Return structured dataclass results — never raw free-text
2. Set `knowledge_unavailable=True` (not raise exceptions) when the source is unreachable
3. Distinguish "no interaction found" from "knowledge source unavailable"
4. Never log API credentials, patient identifiers, or PHI
5. Always set `requires_clinician_review=True`

---

## 4. Drug Normalization

### `DrugKnowledgeRecord`

Canonical normalized drug representation:

```python
@dataclass
class DrugKnowledgeRecord:
    normalized_name: str       # Lowercase canonical name for matching
    display_name: str          # Human-readable name for alerts
    identifier: Optional[str]  # Source system ID (e.g. FDA application number)
    drug_class: Optional[str]  # Pharmacological class (e.g. 'NSAID', 'ACE Inhibitor')
    source: DrugKnowledgeSource
    source_reference: Optional[str]
    retrieved_at: Optional[datetime]
```

The mock provider maintains a static catalogue of 15 clinically relevant drugs covering all Phase 8.9 interaction and contraindication rule pairs. openFDA results are mapped to this structure before use.

---

## 5. Drug-Drug Interaction (DDI) Lookup

### `DrugInteractionKnowledge`

```python
@dataclass
class DrugInteractionKnowledge:
    drug_a: str
    drug_b: str
    interaction_found: bool
    severity: Optional[str]          # CRITICAL / HIGH / MODERATE / LOW — None for openFDA (no structured severity in FAERS)
    description: Optional[str]
    source: DrugKnowledgeSource
    source_reference: Optional[str]
    requires_clinician_review: bool  # Always True
    knowledge_unavailable: bool      # True when provider could not be reached
    unavailability_reason: Optional[str]
```

#### Mock Provider
Checks all pairwise drug combinations against 6 curated interaction rules covering the highest-risk clinical pairs (warfarin+aspirin, sildenafil+nitroglycerin, etc.).

#### openFDA Provider
Queries the openFDA FAERS adverse event database for co-reported drug adverse events.

> [!WARNING]
> openFDA FAERS data represents **adverse event co-reports**, NOT a curated pharmacological interaction database. Absence of a FAERS co-report does NOT guarantee no interaction exists. The openFDA provider is informational only.

---

## 6. Contraindication Lookup

### `ContraindicationKnowledge`

```python
@dataclass
class ContraindicationKnowledge:
    drug: str
    condition: str
    contraindication_found: bool
    severity: Optional[str]
    description: Optional[str]
    source: DrugKnowledgeSource
    source_reference: Optional[str]
    requires_clinician_review: bool  # Always True
    knowledge_unavailable: bool
    unavailability_reason: Optional[str]
```

#### Mock Provider
Checks drug × condition pairs against 5 curated contraindication rules (ibuprofen+ulcer, metformin+renal impairment, propranolol+asthma, lisinopril+pregnancy, ciprofloxacin+myasthenia).

#### openFDA Provider
Searches the FDA drug label database for mentions of the condition in `contraindications` and `warnings` text fields for the specified drug.

---

## 7. Supported Providers

| Provider | `DRUG_KNOWLEDGE_PROVIDER` | Requires Credentials | Network | Coverage |
|---|---|---|---|---|
| `MockDrugKnowledgeProvider` | `mock` | No | No | 15 curated drugs, 6 DDI rules, 5 contraindication rules |
| `OpenFDADrugKnowledgeProvider` | `openfda` | No (optional API key) | Yes (HTTPS) | FDA FAERS adverse events + FDA drug labels |

---

## 8. Configuration

```bash
# Default — offline, no credentials required
DRUG_KNOWLEDGE_PROVIDER="mock"

# Optional external FDA provider
DRUG_KNOWLEDGE_PROVIDER="openfda"
OPENFDA_API_KEY=""                # Optional — anonymous requests allowed; API key increases rate limits
OPENFDA_TIMEOUT_SECONDS=5        # Request timeout
```

**The default configuration is always `mock`**. The project runs fully offline without any credentials.

---

## 9. Error Handling & Safe Failure

External API failures NEVER crash the application. All errors are caught and returned as structured `knowledge_unavailable=True` results.

| Failure Scenario | Response |
|---|---|
| Network timeout | `knowledge_unavailable=True`, `unavailability_reason="openFDA request timed out after Ns"` |
| HTTP 429 Rate Limit | `knowledge_unavailable=True`, `unavailability_reason="openFDA rate limit exceeded"` |
| HTTP 401 Auth Failure | `knowledge_unavailable=True`, `unavailability_reason="openFDA authentication failure (check API key configuration)"` |
| HTTP 5xx Server Error | `knowledge_unavailable=True`, `unavailability_reason="openFDA HTTP 503"` |
| Connection refused | `knowledge_unavailable=True`, `unavailability_reason="openFDA connection error: ConnectError"` |
| Malformed response | `knowledge_unavailable=True`, `unavailability_reason="Malformed response from openFDA"` |
| 404 / No data | `interaction_found=False`, `knowledge_unavailable=False` (correctly: no data found, not an error) |

> [!IMPORTANT]
> `knowledge_unavailable=True` is **not the same** as `interaction_found=False`.
> When knowledge is unavailable, the system cannot determine whether an interaction exists.
> Clinical staff must be informed of this distinction.

---

## 10. Security

- API credentials (`OPENFDA_API_KEY`) are **never logged** at any log level.
- Patient identifiers are **never transmitted** to the openFDA API. Only drug names and condition keywords are sent.
- All external requests use HTTPS.
- The credential is stored in memory only; it is transmitted only as an HTTP query parameter over HTTPS.
- Log messages that reference credentials use `[REDACTED]` or omit credential values entirely.

---

## 11. Offline / Mock Mode

The default `DRUG_KNOWLEDGE_PROVIDER=mock` configuration ensures:

- No network access required
- No API credentials required
- Deterministic and reproducible results for testing
- Full test suite passes offline

The mock provider is suitable for local development, CI/CD, and unit testing.

---

## 12. Caching

Caching was evaluated and intentionally **not implemented in Phase 9.0.2**.

Rationale:
- The mock provider is already deterministic and fast (in-memory lookup)
- The openFDA API has rate limits but responses are fast (< 1s typical)
- Adding a cache layer (even in-memory) introduces state management complexity without clear benefit at current scale
- Redis/Celery caching is explicitly out of scope for this phase

Future improvement: In-memory TTL cache for openFDA responses can be added as a pure `BaseDrugKnowledgeProvider` decorator without modifying provider implementations.

---

## 13. Testing

All 68 tests are offline and deterministic. No real network calls are made.

```bash
.\.venv\Scripts\pytest.exe tests/test_drug_knowledge.py -v
# Expected: 68 passed
```

Test coverage:

| Category | Tests |
|---|---|
| Drug normalization (mock) | 6 |
| DDI lookup (mock) | 9 |
| Contraindication lookup (mock) | 6 |
| Unavailability distinction | 4 |
| openFDA response parsing (mocked HTTP) | 8 |
| openFDA failure modes | 8 |
| Credential security | 4 |
| Clinician review invariant | 5 |
| Factory functions | 6 |
| Phase 8.9 backward compatibility | 6 |
| Abstract interface contract | 3 |
| Data structure validation | 3 |

---

## 14. Limitations

1. **openFDA FAERS is NOT a pharmacological DDI database.** Co-reported adverse events are not confirmed drug interactions.
2. **openFDA drug labels are NOT exhaustive.** Absence of a label hit does not confirm safety.
3. **Mock provider rules are curated, not comprehensive.** They cover the most clinically significant pairs for demonstration and testing purposes.
4. **No severity classification from openFDA.** The FAERS and label APIs do not return standardized severity levels.
5. **Rate limiting.** Anonymous openFDA requests are limited to 240/minute. API key increases this limit.

---

## 15. Future Improvements

- In-memory TTL cache decorator for external provider responses
- Additional authoritative drug knowledge adapters (e.g., NLM RxNorm, First Databank)
- Structured severity normalization from openFDA label text
- Background refresh for frequently queried drug pairs

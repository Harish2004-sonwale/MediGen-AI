# Phase 8.9 Implementation Plan: Longitudinal Clinical Intelligence & Safety Layer

## 1. Current Architecture Review

MediGen-AI has established a clinical AI architecture:
- **Authoritative Data Layer**: PostgreSQL holding patients, doctors, users, encounters, appointments, medical documents, chunks, chat sessions, and messages.
- **Retrieval & Semantic Layer**: ChromaDB with strict `patient_id` metadata isolation, verified against PostgreSQL chunk ownership before synthesis.
- **Synthesis & Streaming**: `BaseLLMProvider` (`MockLLMProvider`, `OpenAILLMProvider`, `BedrockLLMProvider`), SSE streaming (`/messages/stream`), strict grounding, inert `<document_context>` prompt injection defenses, and structured citations.
- **Document Ingestion & OCR**: Multi-format extraction (PDF, DOCX, TXT), `BaseOCRProvider` (`MockOCRProvider`, `TextractOCRProvider`), clinical cleaning, and semantic chunking.
- **RBAC & Isolation**: JWT authentication with strict role checks (`patient`, `doctor`, `healthcare_staff`, `admin`) and doctor-patient active clinical relationship verification.

---

## 2. Phase 8.9 Goals & Capabilities

### 2.1 Longitudinal Clinical Timeline
- **Derived Clinical Event Aggregation**: Assemble chronological events across:
  - Clinical encounters (consultations, outpatient visits, ER visits)
  - Medical appointments (scheduled, completed, cancelled)
  - Medical documents uploaded (lab reports, discharge summaries, prescriptions, clinical notes)
  - Extracted clinical facts from chunks (diagnoses, medication starts, lab findings)
- **Data Model**: `ClinicalTimelineEvent` (`event_id`, `patient_id`, `event_date`, `event_type`, `title`, `description`, `source_document_id`, `source_chunk_id`, `page_number`, `confidence`, `citations`).
- **APIs**:
  - `GET /api/v1/patients/{patient_id}/timeline` — Date filtering (`start_date`, `end_date`), `event_type` filtering, pagination (`skip`, `limit`), sorting (`asc`/`desc`).
  - `GET /api/v1/patients/{patient_id}/timeline/summary` — Grounded longitudinal summary generated via patient-scoped RAG and LLM provider with verified citations.

### 2.2 Clinical Decision Support (CDS) & Safety Layer
- **Safety Checks**:
  1. **Medication Duplication**: Detect duplicate/overlapping medications in patient records.
  2. **Allergy Warnings**: Detect conflicts between known patient allergies and active/candidate medications.
  3. **Drug-Drug Interactions**: Pluggable `BaseDrugInteractionProvider` with deterministic `MockDrugInteractionProvider` and extensible cloud adapter.
  4. **Contraindications**: Pluggable `BaseContraindicationProvider` with `MockContraindicationProvider`.
- **Severity Levels**: `INFO`, `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
- **Disclaimer**: Wording strictly reinforces decision support ("Potential interaction detected. Clinician review required. Does not replace professional medical judgment.").
- **API**:
  - `POST /api/v1/patients/{patient_id}/safety/check` — Runs safety checks on current patient records or against candidate medications submitted in request.

---

## 3. Existing Reusable Components

- `app.services.rag_service.validate_patient_rag_access`: Patient ownership & doctor clinical relationship enforcement.
- `app.services.rag_service.execute_rag_query`: Scoped RAG retrieval with citations.
- `app.ai.llm`: LLM providers and grounded response generation.
- `app.models`: `Patient`, `Doctor`, `Encounter`, `Appointment`, `MedicalDocument`, `DocumentChunk`.

---

## 4. Files Requiring Modification & Creation

### New Files
1. **`backend/app/schemas/timeline.py`**: Pydantic schemas for timeline events, timeline query filters, and timeline summary responses.
2. **`backend/app/schemas/safety.py`**: Pydantic schemas for clinical safety requests, alerts, severity enums, and safety reports.
3. **`backend/app/ai/safety_providers.py`**: Abstract interfaces and mock implementations for drug interactions and contraindications.
4. **`backend/app/services/timeline_service.py`**: Service aggregating authoritative records into chronological timeline events and generating RAG-grounded summaries.
5. **`backend/app/services/safety_service.py`**: Service running medication deduplication, allergy conflict checks, and interaction analysis.
6. **`backend/app/api/v1/endpoints/timeline.py`**: REST router for `/patients/{patient_id}/timeline` and `/timeline/summary`.
7. **`backend/app/api/v1/endpoints/safety.py`**: REST router for `/patients/{patient_id}/safety/check`.
8. **`backend/tests/test_timeline.py`**: Tests for timeline aggregation, filters, sorting, isolation, RBAC, and RAG summary.
9. **`backend/tests/test_safety.py`**: Tests for medication duplication, allergy warnings, drug interactions, contraindications, and patient safety checks.
10. **`docs/phase_8_9_implementation_plan.md`**, **`docs/phase_8_9.md`**, **`docs/clinical_timeline.md`**, **`docs/clinical_safety.md`**.

### Modified Files
1. **`backend/app/schemas/__init__.py`**: Export timeline and safety schemas.
2. **`backend/app/services/__init__.py`**: Export timeline and safety service functions.
3. **`backend/app/api/v1/api.py`**: Register timeline and safety routers.
4. **`docs/api_overview.md`**: Document timeline and safety endpoints.

---

## 5. Database & Migration Analysis

Timeline events and clinical safety reports are generated dynamically from authoritative data (`patients`, `encounters`, `appointments`, `medical_documents`, `document_chunks`). This derived read-model pattern ensures real-time accuracy without stale caches or redundant data storage.
**Conclusion**: No database schema change or new Alembic migration is required.

---

## 6. Security & PHI Guidelines

- **Patient Isolation**: Every timeline and safety query requires patient resolution and strict RBAC verification (`validate_patient_rag_access`).
- **Zero PHI Logging**: Logs contain only event counts, alert counts, and execution durations. No patient clinical data or alert explanations are logged.
- **Prompt Injection Defense**: Longitudinal summaries use `<document_context>` wrappers and strict instruction refusal rules.

---

## 7. Implementation Order

1. **Schemas**: Implement `app/schemas/timeline.py` and `app/schemas/safety.py`.
2. **Safety Providers**: Implement `app/ai/safety_providers.py` (`BaseDrugInteractionProvider`, `MockDrugInteractionProvider`, `BaseContraindicationProvider`, `MockContraindicationProvider`).
3. **Services**: Implement `app/services/timeline_service.py` and `app/services/safety_service.py`.
4. **API Endpoints**: Implement `app/api/v1/endpoints/timeline.py` and `app/api/v1/endpoints/safety.py` and register in `api.py`.
5. **Testing**: Implement `tests/test_timeline.py` and `tests/test_safety.py`.
6. **Validation**: Run full pytest suite, verify Alembic migration chain, verify clean git diff.
7. **Documentation**: Write `docs/phase_8_9.md`, `docs/clinical_timeline.md`, `docs/clinical_safety.md`, and update `docs/api_overview.md`.

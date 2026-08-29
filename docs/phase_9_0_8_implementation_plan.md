# Phase 9.0.8 Implementation Plan — Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation

## 1. Phase Title
**Phase 9.0.8 — Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation**

---

## 2. Business & Technical Goal
The goal of Phase 9.0.8 is to implement a safe, extensible AI Clinical Documentation and Scribe Synthesis engine that automatically drafts structured clinical notes (SOAP notes, consultation notes, discharge summaries, procedure notes, and referral letters) from patient context, multi-turn clinical chat sessions, longitudinal timeline events, and multi-modal imaging findings.

### Core Objectives:
- **Alleviate Clinical Documentation Burden**: Synthesize complex multi-modal patient data and conversation history into standard clinical note formats.
- **Strict Human-in-the-Loop Safety**: All generated notes default to `DRAFT` status and must undergo physician review, editing, and immutable signoff (`FINALIZED`) before becoming authoritative.
- **Interoperability & Export**: Provide structured JSON representations and FHIR R4 `DocumentReference` / `Composition` compatibility.
- **Offline-First & Deterministic**: Provide a deterministic offline `MockClinicalScribeProvider` requiring zero external API keys or GPU dependencies for development and automated testing.

---

## 3. Why This Phase Is the Correct Next Milestone
With Milestones 1–8 and Phases 9.0.1 through 9.0.7 completed, MediGen AI possesses:
1. Relational patient records & encounters (Milestone 4 & 5)
2. Grounded clinical RAG & multi-turn consultation chat (Phase 8.5 & 8.6)
3. Longitudinal timeline aggregation & safety checks (Phase 8.9 & 9.0.2)
4. FHIR R4 ingestion/export (Phase 9.0.1)
5. Background asynchronous worker architecture (Phase 9.0.3)
6. Production observability & metrics (Phase 9.0.4)
7. React 18 frontend dashboard (Phase 9.0.6)
8. Multi-modal diagnostic media & imaging analysis (Phase 9.0.7)

The next logical evolutionary step in the clinical care cycle is **documentation synthesis**: converting these disjointed clinical inputs (encounters, conversations, timeline milestones, drug alerts, and imaging findings) into coherent, structured clinical documentation that clinicians can review, modify, and sign off.

---

## 4. Current Architecture Dependencies
- **PostgreSQL 16 & SQLAlchemy 2.0**: Relational persistence for patients, encounters, users, and media.
- **Pydantic v2**: Strict schema validation for clinical notes, sections, and signoffs.
- **Background Task Worker Pool**: Asynchronous dispatch for heavy LLM note synthesis workloads.
- **FastAPI Core & RBAC**: Strict role enforcement (`DOCTOR`, `HEALTHCARE_STAFF`, `ADMIN`) and patient isolation.
- **React 18 Frontend Dashboard**: Interactive note drafting, section editing, and physician signoff workspace.

---

## 5. Detailed Feature Scope
1. **Clinical Note Types**:
   - `SOAP` (Subjective, Objective, Assessment, Plan)
   - `CONSULTATION` (Consultation notes with history & recommendations)
   - `DISCHARGE_SUMMARY` (Hospital course, discharge medications, follow-up instructions)
   - `PROCEDURE_NOTE` (Pre/post-op diagnosis, procedure details, findings, complications)
   - `REFERRAL_LETTER` (Clinical reason for referral, relevant history, attached findings)
2. **AI Scribe Provider Interface**:
   - `BaseClinicalScribeProvider` with `synthesize_clinical_note(...)`.
   - `MockClinicalScribeProvider` providing deterministic, clinical-grade note structures offline.
3. **Note Lifecycle & Status Management**:
   - `DRAFT`: Initial AI-generated or manually created note; editable by authorized clinicians.
   - `FINALIZED`: Clinician verified, signed off with physician credentials and timestamp; immutable.
   - `AMENDED`: Addendum added by attending physician with version tracking.
4. **Interactive Note Editor Workspace (Frontend)**:
   - Template selection, section-by-section markdown editor, differential inclusion, and one-click physician signoff.

---

## 6. Backend Implementation Plan
1. **Schemas** (`backend/app/schemas/note.py`):
   - `NoteType`: Enum (`soap`, `consultation`, `discharge_summary`, `procedure_note`, `referral_letter`)
   - `NoteStatus`: Enum (`draft`, `finalized`, `amended`)
   - `SOAPContent`: Structured Pydantic model (`subjective`, `objective`, `assessment`, `plan`)
   - `ClinicalNoteCreate`, `ClinicalNoteUpdate`, `ClinicalNoteSignoff`, `ClinicalNoteResponse`, `ClinicalNoteListResponse`
2. **Database Model & Migration** (`backend/app/models/note.py` & Alembic `0010_clinical_notes.py`):
   - `ClinicalNote` ORM model mapped to `clinical_notes` table.
3. **Scribe Provider Architecture** (`backend/app/ai/scribe_provider.py`):
   - Abstract `BaseClinicalScribeProvider` and deterministic `MockClinicalScribeProvider`.
4. **Service Layer** (`backend/app/services/note_service.py`):
   - Synthesis orchestration aggregating patient history, chat session transcript, encounter details, and media findings.
   - Immutable signoff logic and amendment tracking.
5. **Background Task Integration**:
   - Register `BackgroundTaskType.NOTE_SYNTHESIS` in `backend/app/schemas/task.py` and `backend/app/ai/task_worker.py`.
6. **API Endpoints** (`backend/app/api/v1/endpoints/notes.py`):
   - CRUD, async synthesis trigger, and physician signoff endpoints.

---

## 7. Frontend Implementation Plan
1. **Types** (`frontend/src/types/index.ts`):
   - `NoteType`, `NoteStatus`, `SOAPContent`, `ClinicalNote`, `ClinicalNoteListResponse`.
2. **API Client** (`frontend/src/api/client.ts`):
   - `notesApi`: `list`, `get`, `create`, `update`, `synthesize`, `signoff`.
3. **Workspace Component** (`frontend/src/components/notes/ClinicalNoteWorkspace.tsx`):
   - Note listing, dynamic section editor, auto-draft generator, and signoff confirmation banner.
4. **Dashboard Integration** (`frontend/src/pages/DashboardPage.tsx`):
   - Add `📝 Clinical Notes` tab to workspace bar.

---

## 8. Database / Model Changes (Migration `0010_clinical_notes`)
Table: `clinical_notes`
- `id`: Integer Primary Key
- `note_id`: VARCHAR(32) Unique Index (`NOT-YYYYMMDD-XXXXXX`)
- `patient_id`: Integer ForeignKey (`patients.id`, `ondelete="RESTRICT"`, indexed)
- `author_user_id`: Integer ForeignKey (`users.id`, `ondelete="SET NULL"`, nullable)
- `encounter_id`: Integer ForeignKey (`encounters.id`, `ondelete="SET NULL"`, nullable)
- `title`: VARCHAR(255)
- `note_type`: VARCHAR(50) Indexed (`soap`, `consultation`, `discharge_summary`, `procedure_note`, `referral_letter`)
- `status`: VARCHAR(50) Indexed (`draft`, `finalized`, `amended`)
- `content_json`: JSON (Structured sections e.g. SOAP or discharge blocks)
- `raw_text`: TEXT (Rendered note text)
- `is_ai_generated`: Boolean (Default: `true`)
- `requires_clinician_review`: Boolean (Default: `true`)
- `signed_by_user_id`: Integer ForeignKey (`users.id`, nullable)
- `signed_at`: DateTime timezone-aware (Nullable)
- `created_at`: DateTime timezone-aware (Default: `now()`)
- `updated_at`: DateTime timezone-aware (Default: `now()`)

---

## 9. API Endpoint Changes

| HTTP Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/notes` | Doctor, Staff, Admin | Manually draft a clinical note |
| `GET` | `/api/v1/patients/{patient_id}/notes` | Authenticated / Isolated | List clinical notes for patient |
| `GET` | `/api/v1/notes/{note_id}` | Authenticated / Isolated | Retrieve clinical note details |
| `PATCH` | `/api/v1/notes/{note_id}` | Doctor, Staff, Admin | Update draft clinical note contents |
| `POST` | `/api/v1/tasks/notes/synthesize` | Doctor, Staff, Admin | Enqueue background AI note synthesis task |
| `POST` | `/api/v1/notes/{note_id}/signoff` | Doctor, Admin | Attending physician review and final signoff |

---

## 10. AI / RAG / LLM Integration Requirements
- Multi-source context assembly: Aggregates patient demographic profile, encounter assessment, active medications/allergies, chat session messages, and recent diagnostic media findings.
- Section-level structure validation: Produces typed JSON conforming to standard clinical documentation formats.
- Mandatory safety header: Every AI-drafted note is stamped with:
  *"AI Clinical Scribe Draft: Subject to review, amendment, and signature by the attending physician before clinical reliance."*

---

## 11. Background Worker Integration
- Task Type: `BackgroundTaskType.NOTE_SYNTHESIS = "note_synthesis"`.
- Job Function: `execute_note_synthesis_job(patient_id, note_type, encounter_id, session_id, user_id)`.
- Non-blocking execution through `get_background_task_provider()`.

---

## 12. Security, RBAC & Patient Isolation Requirements
- **Patient Data Isolation**: Strict validation preventing cross-patient note access.
- **RBAC**:
  - `PATIENT`: Read-only access to their own finalized notes.
  - `HEALTHCARE_STAFF`: Draft and edit notes; cannot perform final physician signoff.
  - `DOCTOR` & `ADMIN`: Draft, edit, synthesize, and execute final legal signoff.
- **Zero-PHI Logging**: Patient identifiers, note contents, and clinical text are never logged to console or operational telemetry.

---

## 13. Observability & Reliability Requirements
- Scribe synthesis execution latencies and status metrics tracked in `medigen.http` and `TaskMonitor`.
- Graceful degradation: If LLM synthesis encounters an error, the task records failure and returns standard template skeletons for manual clinician completion.

---

## 14. Testing Strategy
1. **Backend Tests** (`backend/tests/test_notes.py`):
   - Scribe provider deterministic synthesis across all 5 note types.
   - Note creation, updating, and validation.
   - Immutability enforcement (prevent editing of `FINALIZED` notes without amendment).
   - Asynchronous background worker execution and progress tracking.
   - RBAC and cross-patient isolation.
2. **Frontend Tests** (`frontend/src/test/notes.test.tsx`):
   - Rendering clinical note list and detail view.
   - Section editor state updates.
   - Physician signoff action and verification banner.
3. **Full Regression Test Suite**:
   - Verify all 322 existing tests continue to pass with 0 regressions.

---

## 15. Deployment Considerations
- Zero new external infrastructure dependencies (runs seamlessly on SQLite for testing and PostgreSQL for production).
- Volume storage unaffected (structured notes stored in PostgreSQL JSON/Text columns).
- Fully compatible with non-root Docker and Compose production configs.

---

## 16. Explicit Non-Goals
- Autonomous medical decision making or automated signing of notes without physician action.
- Direct external billing/coding automated claim submission (reserved for future billing milestone).
- Voice/audio real-time dictation streaming (Phase 9.0.8 focuses on multi-modal contextual synthesis from text/records/imaging).

---

## 17. Risks & Mitigation

| Risk | Impact | Mitigation Strategy |
|---|---|---|
| Unverified AI hallucination in clinical note | High | Enforce `DRAFT` status on creation; require explicit clinician signoff before finalizing. |
| Inadvertent modification of signed clinical notes | Critical | DB & service level immutability check: `FINALIZED` notes cannot be updated via PATCH. |
| Database migration locks | Low | Additive table creation with single-column indices; zero alterations to existing tables. |

---

## 18. Rollback Strategy
- Alembic downgrade: `alembic downgrade -1` cleanly drops `clinical_notes` table and associated indices.
- Frontend backward compatibility: Tab is non-intrusive and can be toggled via feature flags.

---

## 19. Exact Files Expected to Be Created / Modified

### New Files:
- `backend/alembic/versions/0010_clinical_notes.py`
- `backend/app/models/note.py`
- `backend/app/schemas/note.py`
- `backend/app/ai/scribe_provider.py`
- `backend/app/services/note_service.py`
- `backend/app/api/v1/endpoints/notes.py`
- `backend/tests/test_notes.py`
- `docs/phase_9_0_8.md`
- `frontend/src/components/notes/ClinicalNoteWorkspace.tsx`
- `frontend/src/test/notes.test.tsx`

### Modified Files:
- `backend/app/models/__init__.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/task.py`
- `backend/app/api/v1/api.py`
- `backend/app/core/config.py`
- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `README.md`

---

## 20. Detailed Verification Plan
1. **Alembic Validation**: `alembic upgrade head --sql` to verify DDL generation.
2. **Backend Unit & Integration Tests**: `pytest backend/tests/test_notes.py -v`.
3. **Full Backend Regression**: `pytest backend/tests -q` (Target: 330+ passing).
4. **Frontend Unit Tests**: `npm run test -- --run` in `frontend` directory.
5. **Frontend Production Build**: `npm run build` to verify clean TypeScript compilation and bundle generation.
6. **Code Formatting & Security**: `git diff --check` and secret audit.

---

## 21. Definition of Done
- All 10 new files and 9 modified files implemented cleanly.
- 100% test pass rate across backend and frontend suites.
- Migration 0010 verified on PostgreSQL and SQLite.
- Complete documentation in `docs/phase_9_0_8.md` and `README.md`.
- Clean Git status ready for commit and push.

---

## 22. Future Roadmap After Phase 9.0.8
- **Phase 9.0.9 — Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion**
- **Phase 9.1.0 — Enterprise EHR Integration (SMART on FHIR & OAuth2 SSO)**

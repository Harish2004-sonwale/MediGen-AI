# Phase 9.0.8 — Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation

## Overview
Phase 9.0.8 delivers an automated AI Clinical Documentation and Scribe Synthesis engine capable of synthesizing multi-turn clinical chat sessions, longitudinal timeline events, clinical encounters, lab/diagnostic observations, and multi-modal imaging findings into structured, standardized clinical documentation (SOAP Notes, Consultation Summaries, Discharge Summaries, Procedure Notes, and Clinical Referral Letters).

---

## 1. Key Architectural Components

### 1.1 Data Model (`ClinicalNote`)
- **Table**: `clinical_notes` (Alembic migration `0010_clinical_notes.py`)
- **Identifiers**: Unique public identifiers format `NOT-YYYYMMDD-XXXXXX`
- **Fields**:
  - `note_id`: Public alphanumeric identifier
  - `patient_id`: Foreign key reference with strict isolation
  - `author_user_id`: ID of the authoring clinician
  - `encounter_id`: Optional associated clinical encounter
  - `title`: Descriptive clinical note title
  - `note_type`: `soap`, `consultation`, `discharge_summary`, `procedure_note`, `referral_letter`
  - `status`: `draft`, `finalized`, `amended`
  - `content_json`: Structured section representation
  - `raw_text`: Complete rendered note narrative
  - `is_ai_generated`: Boolean indicator for AI assistance
  - `requires_clinician_review`: Default `true`
  - `signed_by_user_id` & `signed_at`: Attending physician signoff audit trail

### 1.2 Clinical Scribe Provider (`BaseClinicalScribeProvider`)
- **Abstract Base Class**: `BaseClinicalScribeProvider` (`app.ai.scribe_provider`)
- **Deterministic Mock Implementation**: `MockClinicalScribeProvider`
  - Offline-first with zero external API key requirements.
  - Multi-source contextual assembly across patient demographic details, active medications, allergies, diagnostic imaging summaries, and custom clinician directives.
  - Mandatory assistive disclaimer appended to all AI-generated drafts.

### 1.3 Immutability & Clinical Safety Invariants
- **Drafting Status**: All AI-synthesized notes default to `status = draft` and `requires_clinician_review = true`.
- **Physician Legal Signoff**: Finalization requires an explicit acknowledgement of review (`confirm_accuracy = true`) by a user with `DOCTOR` or `ADMIN` role.
- **Immutability Enforcement**: Once transitioned to `finalized`, direct modification via `PATCH` is strictly forbidden and returns `400 Bad Request`.

---

## 2. API Endpoints

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/notes` | Doctor, Staff, Admin | Manually draft a clinical note |
| `GET` | `/api/v1/patients/{patient_id}/notes` | Clinical Roles / Own Patient | List notes for a patient |
| `GET` | `/api/v1/notes/{note_id}` | Clinical Roles / Own Patient | Retrieve note details & narrative |
| `PATCH` | `/api/v1/notes/{note_id}` | Doctor, Staff, Admin | Update draft clinical note |
| `POST` | `/api/v1/tasks/notes/synthesize` | Doctor, Staff, Admin | Enqueue async background AI scribe synthesis |
| `POST` | `/api/v1/notes/{note_id}/signoff` | Doctor, Admin | Attending physician review and legal signoff |

---

## 3. Frontend Clinical Note Workspace
- **Component**: `ClinicalNoteWorkspace.tsx` (`frontend/src/components/notes/ClinicalNoteWorkspace.tsx`)
- **Features**:
  - Interactive note list with status badges (`Draft`, `Finalized`).
  - Note template selection (`SOAP`, `Consultation`, `Discharge Summary`, `Procedure Note`, `Referral Letter`).
  - Asynchronous AI Scribe synthesis trigger with task monitor integration.
  - Section editor and pre-formatted narrative viewer.
  - Attending physician verification checkbox, addendum remarks, and one-click legal signoff.

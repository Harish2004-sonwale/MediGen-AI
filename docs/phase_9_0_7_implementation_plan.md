# Phase 9.0.7 Implementation Plan — Advanced Multi-Modal Medical Diagnostics & Imaging Support

## 1. Current Architecture Assessment
The current MediGen AI platform features:
- **FastAPI Core**: Secure REST & SSE API with strict RBAC (`admin`, `doctor`, `healthcare_staff`, `patient`) and patient isolation.
- **PostgreSQL 16 Storage**: Authoritative relational tables for Patients, Doctors, Encounters, Appointments, Documents, Chunks, and Chat.
- **Clinical AI Layer**: Multi-turn RAG, Bedrock/Mock LLM providers, deterministic safety CDS engine, and authoritative drug knowledge adapters.
- **Background Async Worker**: Thread-safe task worker pool supporting `document_processing`, `timeline_summary`, `safety_check`, and `batch_indexing`.
- **Production Deployment**: Hardened multi-stage non-root Docker, zero-secret environment validation, and automated logging redaction.
- **Frontend Dashboard**: React 18 + Vite + TypeScript SPA with responsive patient workspace, real-time SSE streaming copilot, and CDS prescriber.

---

## 2. Proposed Architecture for Phase 9.0.7

### 2.1 Domain Model & Media Abstraction
We introduce a dedicated, first-class clinical media entity `DiagnosticMedia`:
- **File & Binary Handling**: Raw image binaries (JPEG, PNG, DICOM, TIFF, WebP, PDF) are stored in the local file system / object store root (`settings.MEDIA_STORAGE_DIR`), while PostgreSQL retains all authoritative metadata, modality attributes, patient links, and analysis results.
- **Modality Support**: Chest X-Ray (`XRAY_CHEST`), CT Scan (`CT_SCAN`), MRI (`MRI`), Ultrasound (`ULTRASOUND`), Dermatology (`DERMATOLOGY`), Pathology (`PATHOLOGY`), and General (`OTHER`).
- **Clinician Review Invariant**: Every automated analysis defaults to `requires_clinician_review = True` and `clinician_confirmed = False`. AI findings are explicitly flagged as decision support, never autonomous diagnoses.

### 2.2 End-to-End Multi-Modal Data Flow
```
1. Image Upload (POST /api/v1/patients/{id}/media)
   │
   ├─ MIME/Magic Byte & Extension Validation
   ├─ Path Traversal Sanitization & Patient Ownership Check
   └─ Media Record Created (Status: UPLOADED) in PostgreSQL
   │
2. Asynchronous Analysis Task Enqueued (POST /api/v1/tasks/media/{id}/analyze)
   │
   ├─ Background Worker Worker Pool dequeues task
   ├─ Worker invokes BaseMedicalImagingProvider.analyze_image(...)
   ├─ Imaging Provider generates StructuredImagingFinding (findings, confidence, anomalies)
   └─ Result persisted in DiagnosticMedia (Status: ANALYZED)
   │
3. Clinical Verification & RAG Integration
   │
   ├─ Clinician views image & AI findings in Frontend Dashboard
   ├─ Clinician confirms/overrides findings (POST /api/v1/media/{id}/review)
   └─ Structured findings indexed into Patient Timeline & Clinical RAG
```

---

## 3. Provider Abstraction (`BaseMedicalImagingProvider`)

```python
class BaseMedicalImagingProvider(ABC):
    """Abstract base class for multi-modal medical imaging analysis."""

    @abstractmethod
    def analyze_image(
        self,
        file_path: str,
        modality: MediaModality,
        clinical_context: Optional[str] = None,
    ) -> StructuredImagingFinding:
        """Execute clinical image analysis returning structured diagnostic observations."""
        pass
```

### Deterministic Mock Implementation
- `MockMedicalImagingProvider` generates deterministic clinical observations based on modality and image dimensions, with confidence scores (e.g. `0.88–0.96`), anatomical body sites, detected patterns (e.g. `Clear lung fields`, `No acute intracranial hemorrhage`), and mandatory disclaimers.
- Default execution is 100% offline with zero external network or GPU requirements.

---

## 4. API Endpoints Proposed

| HTTP Method | Endpoint | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/media` | Doctor, Staff, Admin | Upload medical image/media with metadata |
| `GET` | `/api/v1/patients/{patient_id}/media` | Clinical Roles / Own Patient | List clinical media for patient |
| `GET` | `/api/v1/media/{media_id}` | Clinical Roles / Own Patient | Retrieve media details & AI findings |
| `GET` | `/api/v1/media/{media_id}/file` | Clinical Roles / Own Patient | Download/stream authorized media image binary |
| `POST` | `/api/v1/tasks/media/{media_id}/analyze` | Doctor, Staff, Admin | Enqueue background AI imaging analysis task |
| `POST` | `/api/v1/media/{media_id}/review` | Doctor, Admin | Clinician confirmation, review notes & signoff |

---

## 5. Database Schema Changes (Migration 0009)

Table: `diagnostic_media`
- `id` (Integer PK)
- `media_id` (VARCHAR(32), unique index, e.g. `MED-YYYYMMDD-XXXXXX`)
- `patient_id` (Integer FK -> `patients.id`, index)
- `uploader_user_id` (Integer FK -> `users.id`, nullable)
- `encounter_id` (Integer FK -> `encounters.id`, nullable)
- `title` (VARCHAR(255))
- `modality` (VARCHAR(50), enum: `xray_chest`, `ct_scan`, `mri`, `ultrasound`, `dermatology`, `pathology`, `other`)
- `body_site` (VARCHAR(100), nullable)
- `original_filename` (VARCHAR(255))
- `file_extension` (VARCHAR(20))
- `file_size_bytes` (Integer)
- `storage_path` (VARCHAR(500))
- `mime_type` (VARCHAR(100))
- `status` (VARCHAR(50), default: `uploaded`)
- `confidence_score` (Float, nullable)
- `findings_summary` (TEXT, nullable)
- `structured_findings` (JSON, nullable)
- `anomalies_detected` (JSON, nullable)
- `requires_clinician_review` (Boolean, default True)
- `clinician_confirmed` (Boolean, default False)
- `clinician_notes` (TEXT, nullable)
- `created_at` (DateTime with timezone)
- `analyzed_at` (DateTime with timezone, nullable)
- `reviewed_at` (DateTime with timezone, nullable)

---

## 6. Frontend Multi-Modal Diagnostics Workspace
Integrate a new **🖼️ Medical Diagnostics & Imaging** tab in `DashboardPage.tsx`:
- **Media Dropzone**: Upload images with modality & body site selectors.
- **Image Gallery & Viewer**: Thumbnail list with status badges (`Analyzing...`, `Ready for Review`, `Confirmed`).
- **AI Findings Card**:
  - Confidence Gauge / Score (`e.g. 92% Confidence`)
  - Detected Observations & Anatomical Region
  - Clinician Review Banner & Signoff Form (Confirm / Override findings)
  - Clear Clinical Safety Disclaimer

---

## 7. Safety, Security & PHI Invariants
- **Non-Autonomous**: Explicit warning: *"AI decision support finding only. Must be validated by a certified radiologist/clinician."*
- **Path Traversal Protection**: Unique hash filenames (`uuid4`), strict storage directory enforcement, zero reliance on user-provided filenames.
- **Patient Isolation**: All media queries joined with authorized patient records and RBAC policies.
- **Zero Secrets & Zero PHI in Logs**: Structured logs contain only sanitized `media_id` and `patient_id` references, never image payloads or raw names.

---

## 8. Testing Strategy
- `test_media_upload.py`: File type validation, size limits, patient isolation, path traversal prevention.
- `test_imaging_provider.py`: Mock provider determinism, structured finding schemas, confidence score ranges.
- `test_media_task.py`: Async background analysis lifecycle (`queued` -> `running` -> `completed`), failure recovery.
- `test_media_review.py`: Clinician confirmation signoff, review permissions, RBAC checks.
- `frontend/src/test/media.test.tsx`: Media gallery rendering, AI findings display, review signoff UI.
- Backend regression: Existing 315 tests must remain 100% passing.

---

## 9. Explicit Non-Goals for Phase 9.0.7
- ❌ Do NOT connect to unverified paid external AI imaging APIs.
- ❌ Do NOT install heavy binary C++ DICOM parser libraries that break cross-platform setups.
- ❌ Do NOT allow autonomous prescription or automated patient diagnostic notifications without clinician review.

---

## 10. Step-by-Step Implementation Order
1. Define Pydantic schemas in `backend/app/schemas/media.py`.
2. Define SQLAlchemy model `DiagnosticMedia` in `backend/app/models/media.py` and create Alembic migration `0009_diagnostic_media.py`.
3. Implement `BaseMedicalImagingProvider` and `MockMedicalImagingProvider` in `backend/app/ai/imaging_provider.py`.
4. Extend `BackgroundTaskType` and task worker in `backend/app/ai/task_worker.py` with `MEDIA_ANALYSIS`.
5. Implement `MediaService` in `backend/app/services/media_service.py`.
6. Implement API endpoints in `backend/app/api/v1/endpoints/media.py` and register in `api.py`.
7. Add comprehensive unit and integration tests in `backend/tests/test_media.py`.
8. Update frontend client `api/client.ts`, types, and create `MediaDiagnosticsHub.tsx` component.
9. Verify frontend build and full backend regression suite (315+ tests).
10. Finalize documentation in `docs/phase_9_0_7.md` and update `README.md`.

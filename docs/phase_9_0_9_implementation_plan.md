# Phase 9.0.9 Implementation Plan — Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion

## 1. Phase Title & Overview
**Phase 9.0.9 — Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion**

### 1.1 Objective
To establish a high-performance, deterministic, and clinically safe Real-Time Vital Telemetry Ingestion and Clinical Decision Support (CDS) Alerting architecture for MediGen AI. This phase bridges real-time patient physiological streaming with persistent, lifecycle-managed clinical safety alerts (medication, DDI, allergy, contraindication, and vital threshold alarms), complete with alarm-fatigue suppression, physician acknowledgement audit trails, and FHIR R4 `Observation` interoperability.

---

## 2. Current Architecture Assessment & Deduplication Analysis
The existing codebase currently features:
- **Milestone 5 (Encounters)** & **Milestone 8.9 (Clinical Safety)**: In-memory safety analysis generating transient `ClinicalSafetyReport` containing medication duplicates, allergy conflicts, and drug interactions.
- **Phase 9.0.1 (FHIR Interoperability)**: Dynamic export of encounters, conditions, and medication statements to FHIR R4.
- **Phase 9.0.3 (Background Worker Architecture)**: `LocalBackgroundTaskProvider`, `SyncBackgroundTaskProvider`, and `CeleryBackgroundTaskProvider` executing asynchronous workloads.
- **Phase 9.0.4 (Observability)**: Prometheus metrics, structured correlation logging, and zero-PHI audit logging.
- **Phase 9.0.6 (Frontend Dashboard)** & **Phase 9.0.7 / 9.0.8 (Media & Notes)**: React 18 + Vite + TypeScript interface with specialized tabs for Chat, Timeline, Documents, Imaging, and Notes.

### What is Missing (To Be Implemented in Phase 9.0.9 without Duplication):
1. **Persistent Vital Telemetry Store**: No table currently exists to record structured multi-parameter physiological telemetry (Heart Rate, Systolic/Diastolic BP, SpO2, Respiratory Rate, Temperature, Weight) with timestamps, source devices, and unit normalization.
2. **Persistent CDS Alert Records & Lifecycle**: Current safety alerts are purely transient evaluations. There is no persistent `clinical_alerts` table tracking alert lifecycle (`ACTIVE`, `ACKNOWLEDGED`, `DISMISSED`, `RESOLVED`) or clinician signoff/acknowledgement audit logs.
3. **Vital Threshold & Trend Evaluation Engine**: An automated deterministic rule engine that evaluates incoming telemetry against standard clinical thresholds (e.g. Critical Hypoxia SpO2 < 90%, Severe Hypertension SBP > 180 mmHg, Extreme Bradycardia/Tachycardia) and raises persistent alerts.
4. **Alarm Fatigue Debouncing & Duplicate Suppression**: Logic to prevent spamming clinicians with redundant alerts within a cooldown window.
5. **Interactive Telemetry & Alert Workspace UI**: Frontend telemetry dashboard showing real-time vital gauges, trend charts, and an interactive CDS alert management banner with one-click acknowledgement.

---

## 3. Core Architectural Capabilities

### 3.1 Structured Vital Telemetry Ingestion
- **Physiological Parameters**:
  - `heart_rate` (bpm, valid range: 20–300)
  - `systolic_bp` & `diastolic_bp` (mmHg, valid range: 30–300 / 20–200)
  - `respiratory_rate` (breaths/min, valid range: 4–60)
  - `temperature_c` (Celsius, normalized from °F if needed, valid range: 25.0–45.0)
  - `spo2_percent` (%, valid range: 50.0–100.0)
  - `weight_kg` (kg, optional, valid range: 0.5–500.0)
- **Metadata**: Source device identifier (`device_id`), measurement timestamp (`measured_at`), data origin (`telemetry_monitor`, `manual_entry`, `simulator`).
- **Validation & Sanitization**: Strict Pydantic v2 range validators preventing corrupt or spoofed sensor data.
- **FHIR Compatibility**: Automatic mapping to standard LOINC codes (8867-4 for HR, 8480-6 for Sys BP, 8462-4 for Dia BP, 9279-1 for Resp Rate, 8310-5 for Body Temp, 2708-6 for SpO2, 29463-7 for Weight).

### 3.2 Clinical Decision Support Alerting Engine
- **Alert Severities**: `INFO`, `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
- **Alert Categories**:
  - `ABNORMAL_VITAL` (Hypoxia, Tachycardia, Bradycardia, Severe Hypertension, Hypotension, Hyperthermia)
  - `MEDICATION_DUPLICATE` (Therapeutic redundancy)
  - `ALLERGY_WARNING` (Direct allergy conflict)
  - `DRUG_INTERACTION` (Major/Critical DDI)
  - `CONTRAINDICATION` (Condition-medication conflict)
- **Lifecycle States**:
  - `ACTIVE`: Newly generated alert awaiting clinician review.
  - `ACKNOWLEDGED`: Clinician has reviewed and taken clinical note.
  - `DISMISSED`: Clinician has dismissed alert with a mandatory clinical reason.
  - `RESOLVED`: Underlying physiological anomaly returned to normal baseline.
- **Alarm Fatigue Mitigation (Debouncing)**:
  - Suppression window (default: 30 minutes) for identical alert signatures per patient.
  - Recurring alerts update `recurrence_count` and `last_triggered_at` rather than creating spam records.

### 3.3 Offline Deterministic Simulator (`MockTelemetrySimulator`)
- Provides offline simulated streams of normal, fluctuating, and critical vitals for automated testing and UI development without requiring physical IoT medical devices.

---

## 4. Database Changes (Migration `0011_vitals_and_clinical_alerts`)

### 4.1 Table: `vital_telemetry`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | Internal ID |
| `reading_id` | String(32) | Unique Index, Not Null | Unique public ID (`VIT-YYYYMMDD-XXXXXX`) |
| `patient_id` | Integer | FK -> `patients.id` (RESTRICT), Index | Associated patient |
| `encounter_id` | Integer | FK -> `encounters.id` (SET NULL), Nullable | Associated clinical encounter |
| `heart_rate` | Integer | Nullable | Heart rate in bpm |
| `systolic_bp` | Integer | Nullable | Systolic blood pressure in mmHg |
| `diastolic_bp` | Integer | Nullable | Diastolic blood pressure in mmHg |
| `respiratory_rate` | Integer | Nullable | Respiratory rate in breaths/min |
| `temperature_c` | Float | Nullable | Body temperature in Celsius |
| `spo2_percent` | Float | Nullable | Blood oxygen saturation percentage |
| `weight_kg` | Float | Nullable | Body weight in kilograms |
| `device_id` | String(64) | Nullable | Source telemetry device / monitor ID |
| `source` | String(50) | Default: 'manual_entry' | Ingestion source ('simulator', 'monitor', 'manual') |
| `measured_at` | DateTime(tz) | Not Null, Index | Timestamp when measurements were recorded |
| `created_at` | DateTime(tz) | Default: now(), Not Null | Database insertion timestamp |

### 4.2 Table: `clinical_alerts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | Internal ID |
| `alert_id` | String(32) | Unique Index, Not Null | Unique public ID (`ALT-YYYYMMDD-XXXXXX`) |
| `patient_id` | Integer | FK -> `patients.id` (RESTRICT), Index | Associated patient |
| `encounter_id` | Integer | FK -> `encounters.id` (SET NULL), Nullable | Associated clinical encounter |
| `reading_id` | Integer | FK -> `vital_telemetry.id` (SET NULL), Nullable | Associated telemetry reading |
| `alert_type` | String(50) | Not Null, Index | `abnormal_vital`, `drug_interaction`, `allergy_warning`, etc. |
| `severity` | String(20) | Not Null, Index | `INFO`, `LOW`, `MODERATE`, `HIGH`, `CRITICAL` |
| `status` | String(20) | Default: 'active', Index | `active`, `acknowledged`, `dismissed`, `resolved` |
| `title` | String(255) | Not Null | Concise alert title (e.g. 'Critical Hypoxia (SpO2 86%)') |
| `explanation` | Text | Not Null | Detailed clinical rationale and guideline reference |
| `parameters_json` | JSON | Nullable | Snapshot of values triggering the alert |
| `recurrence_count` | Integer | Default: 1 | Count of debounced alert occurrences |
| `acknowledged_by_user_id` | Integer | FK -> `users.id` (SET NULL), Nullable | Reviewing clinician ID |
| `acknowledged_at` | DateTime(tz) | Nullable | Timestamp of clinician acknowledgement |
| `dismissal_reason` | Text | Nullable | Clinician rationale for dismissal |
| `last_triggered_at` | DateTime(tz) | Default: now(), Not Null | Timestamp of most recent trigger |
| `created_at` | DateTime(tz) | Default: now(), Not Null | Initial creation timestamp |

---

## 5. API Endpoint Specifications

| HTTP Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/vitals` | Doctor, Staff, Admin | Ingest a new vital telemetry reading and evaluate CDS alerts |
| `GET` | `/api/v1/patients/{patient_id}/vitals` | Authenticated / Isolated | List historical vital telemetry readings (with limit & pagination) |
| `GET` | `/api/v1/patients/{patient_id}/vitals/latest` | Authenticated / Isolated | Retrieve the latest recorded vital telemetry snapshot |
| `POST` | `/api/v1/patients/{patient_id}/vitals/simulate` | Doctor, Staff, Admin | Ingest a simulated vital reading (Normal, Hypoxic, Tachycardic, etc.) |
| `GET` | `/api/v1/patients/{patient_id}/alerts` | Authenticated / Isolated | List active and historical CDS alerts for patient |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Doctor, Staff, Admin | Clinician acknowledges an active CDS alert |
| `POST` | `/api/v1/alerts/{alert_id}/dismiss` | Doctor, Staff, Admin | Clinician dismisses a CDS alert with a mandatory clinical reason |
| `GET` | `/api/v1/alerts/{alert_id}` | Authenticated / Isolated | Retrieve specific alert details and parameter snapshot |

---

## 6. Real-Time Processing & Worker Integration
- **Direct Synchronous Path**: Ingesting a reading synchronously evaluates threshold rules (<10ms) and creates any active alerts immediately so that clinicians receive immediate feedback.
- **Asynchronous Batch Path**: Large historical telemetry ingestions or background sensor feeds submit a `BackgroundTaskType.TELEMETRY_EVALUATION` job.
- **Zero-PHI Telemetry Logging**: Metric logs increment `medigen_vital_readings_total` and `medigen_clinical_alerts_total{severity="..."}` without printing patient identifiers or medical values.

---

## 7. Frontend Telemetry & Alerting Workspace
1. **Component**: `frontend/src/components/telemetry/VitalTelemetryWorkspace.tsx`
   - Real-time vital cards displaying latest Heart Rate, Blood Pressure, Respiratory Rate, Temperature, and SpO2 with color-coded physiologic status (Normal, Warning, Critical).
   - "⚡ Ingest Simulated Vitals" dropdown (Normal, Severe Hypoxia, Hypertensive Crisis, Tachycardia).
   - Historical telemetry table with timestamps and trend indicators.
2. **Component**: `frontend/src/components/telemetry/CDSAlertBanner.tsx`
   - Prominent, color-coded alert stack for `HIGH` and `CRITICAL` alerts.
   - Action controls: "Acknowledge" and "Dismiss (with reason)".
   - Assistive safety badge: *"Clinical Decision Support Alert: Review and clinical judgment required."*
3. **Integration**: Added as `💓 Vitals & CDS Alerts` tab in `frontend/src/pages/DashboardPage.tsx`.

---

## 8. Security, RBAC & Patient Isolation
- **RBAC Enforcement**:
  - `PATIENT`: Read-only view of their own vitals and alerts.
  - `HEALTHCARE_STAFF`: Ingest vitals, acknowledge alerts, dismiss alerts.
  - `DOCTOR` & `ADMIN`: Full ingestion, acknowledgement, dismissal, and resolution control.
- **Patient Isolation**: Cross-patient vital ingestion or alert modification is blocked with `403 Forbidden`.
- **Sanitization**: Values are validated against physiological bounds to prevent malicious integer/float injection or sensor spoofing.

---

## 9. Testing & Quality Assurance Plan
1. **Backend Tests (`backend/tests/test_vitals_and_alerts.py`)**:
   - Vital telemetry validation (valid parameters, out-of-bounds rejection, temperature unit normalization).
   - Deterministic rule engine threshold evaluation (SpO2, Blood Pressure, Heart Rate).
   - Duplicate alert suppression within debouncing window.
   - Alert lifecycle state transitions (`active` -> `acknowledged` -> `dismissed`).
   - Telemetry simulator profiles.
   - RBAC and cross-patient isolation verification.
2. **Frontend Tests (`frontend/src/test/telemetry.test.tsx`)**:
   - Vital telemetry workspace rendering and metric cards.
   - CDS alert banner rendering and dismissal workflow.
   - Simulation trigger.
3. **Full Regression Validation**:
   - Complete test execution against all 327 existing backend tests and 13 frontend tests.

---

## 10. Explicit Non-Goals
- No autonomous diagnosis or automated treatment order execution.
- No direct closed-loop medical device hardware control or infusion pump modifications.
- No mandatory third-party commercial cloud telemetry streaming services.
- No storage of raw binary sensor waveforms (focus on structured physiological readings).

---

## 11. Exact Files Planned to Be Created / Modified

### New Files (10):
1. `backend/alembic/versions/0011_vitals_and_clinical_alerts.py`
2. `backend/app/models/vital.py`
3. `backend/app/models/alert.py`
4. `backend/app/schemas/vital.py`
5. `backend/app/schemas/alert.py`
6. `backend/app/services/vital_service.py`
7. `backend/app/api/v1/endpoints/vitals.py`
8. `backend/tests/test_vitals_and_alerts.py`
9. `docs/phase_9_0_9.md`
10. `frontend/src/components/telemetry/VitalTelemetryWorkspace.tsx`
11. `frontend/src/test/telemetry.test.tsx`

### Modified Files (8):
1. `backend/app/models/__init__.py`
2. `backend/app/schemas/__init__.py`
3. `backend/app/schemas/task.py`
4. `backend/app/api/v1/api.py`
5. `frontend/src/types/index.ts`
6. `frontend/src/api/client.ts`
7. `frontend/src/pages/DashboardPage.tsx`
8. `README.md`

---

## 12. Rollback Strategy
- Alembic downgrade: `alembic downgrade -1` cleanly removes `clinical_alerts` and `vital_telemetry` tables.
- Zero breaking changes to existing patient, encounter, or document models.

---

## 13. Definition of Done
- All backend models, schemas, services, and endpoints implemented and verified.
- Alembic migration `0011` validated with clean SQL generation.
- 100% test pass rate across backend and frontend suites with zero regressions.
- Complete documentation in `docs/phase_9_0_9.md` and updated `README.md`.

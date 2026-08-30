# Phase 9.0.13 Implementation Plan: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking

## Executive Summary & Background Context
MediGen-AI has successfully established core clinical capabilities spanning multi-modal diagnostics, automated clinical note synthesis, real-time vitals telemetry/CDS alerting, longitudinal care plans, population cohort analytics, and structured care transitions/discharge protocols.

The next critical clinical foundation is **Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking**. In hospital and ambulatory medicine, diagnostic and therapeutic orders (labs, radiology, medications, nursing procedures, consults) drive care execution. Closing the loop on pending diagnostic tests, identifying duplicate or redundant orders, detecting critical/panic test results (e.g. Troponin spikes, hyperkalemia, acute anemia), and ensuring mandatory clinician review prevents diagnostic delays and adverse patient outcomes.

---

## User Review Required

> [!IMPORTANT]
> **Clinician-in-the-Loop Order Placement & Result Signoff**:
> - AI-suggested order sets (e.g. Sepsis protocol, Chest pain / ACS bundle, Diabetic Ketoacidosis protocol) will be generated strictly in `DRAFT` status and must be validated and signed by authorized clinicians (`doctor` or `admin`).
> - Critical/panic lab findings require mandatory explicit clinician acknowledgment with timestamped verification to maintain closed-loop diagnostic governance.

---

## Proposed System Architecture

### 1. Database Layer (Migration `0015_clinical_orders_and_diagnostic_results.py`)
- **`clinical_orders`**:
  - `id`, `order_id` (`ORD-YYYYMMDD-HEX`), `patient_id` (FK), `encounter_id` (FK, nullable), `ordering_user_id` (FK to `users`), `order_category` (`laboratory`, `imaging`, `medication`, `nursing`, `consultation`), `order_type` (e.g. `cbc_with_diff`, `basic_metabolic_panel`, `chest_xray_pa`, `ct_head_without_contrast`, `cardiology_consult`), `priority` (`routine`, `urgent`, `stat`), `status` (`draft`, `placed`, `in_progress`, `completed`, `cancelled`), `clinical_indication`, `specimen_source`, `order_details_json`, `ai_safety_flags_json`, `is_ai_suggested`, `placed_at`, `completed_at`, `created_at`, `updated_at`.
- **`diagnostic_results`**:
  - `id`, `result_id` (`RES-YYYYMMDD-HEX`), `order_id` (FK to `clinical_orders`), `patient_id` (FK to `patients`), `encounter_id` (FK, nullable), `test_name`, `test_code_loinc`, `status` (`preliminary`, `final`, `amended`, `corrected`), `abnormal_flag` (`normal`, `abnormal_low`, `abnormal_high`, `panic_critical`), `findings_summary`, `numeric_value`, `unit_of_measure`, `reference_range_low`, `reference_range_high`, `critical_threshold_low`, `critical_threshold_high`, `structured_components_json`, `reviewed_by_user_id` (FK to `users`, nullable), `reviewed_at`, `resulted_at`, `created_at`, `updated_at`.

### 2. Deterministic AI Provider & Verification Engine
- `BaseOrderVerificationProvider` and `MockOrderVerificationProvider` in `backend/app/ai/order_provider.py`:
  - **Order Set Synthesis**: Heuristically constructs standardized order bundles based on chief complaint or assessment (e.g., Acute Chest Pain $\rightarrow$ STAT ECG, Troponin I, CMP, CBC, Chest X-ray; Sepsis $\rightarrow$ Blood Cultures x2, Lactate, CBC, CMP, IV Fluid bolus).
  - **Pre-Order Verification & Duplicate Checking**: Identifies orders of the same type placed within the preceding 24–48 hours and flags potential drug-lab or clinical contraindications (e.g. IV contrast ordered with elevated creatinine / acute kidney injury).
  - **Panic/Critical Result Tagging**: Evaluates structured lab values against age- and condition-adjusted critical thresholds (e.g., Potassium $<2.8$ or $>6.0$ mEq/L, Troponin $\ge 0.04$ ng/mL, Platelets $<50 \times 10^3/\mu\text{L}$, Hemoglobin $<7.0$ g/dL).

### 3. Service Layer (`backend/app/services/order_service.py`)
- Order management CRUD and state transitions (`draft` $\rightarrow$ `placed` $\rightarrow$ `in_progress` $\rightarrow$ `completed` / `cancelled`).
- Order set synthesis and automated pre-order safety validation.
- Diagnostic result ingestion, abnormal flag classification, and critical result notification generation.
- Clinician result review and formal signoff workflow.
- Background worker execution for `ORDER_VERIFICATION` and `RESULT_INGESTION`.

### 4. FHIR R4 Interoperability
- **`ServiceRequest`**: Maps `ClinicalOrder` for laboratory, diagnostic imaging, and consultation requests.
- **`DiagnosticReport`**: Maps `DiagnosticResult` with LOINC coding, multi-component result parameters, observation references, and abnormal status flags.
- Export endpoints: `GET /api/v1/fhir/ServiceRequest/{order_id}` and `GET /api/v1/fhir/DiagnosticReport/{result_id}`.

### 5. REST API Endpoints (`backend/app/api/v1/endpoints/orders.py`)
- `POST /api/v1/patients/{patient_id}/orders`: Create clinical order.
- `POST /api/v1/patients/{patient_id}/orders/suggest-bundle`: AI order set synthesis.
- `GET /api/v1/patients/{patient_id}/orders`: List clinical orders with status and category filtering.
- `GET /api/v1/orders/{order_id}`: Get order details and linked results.
- `PATCH /api/v1/orders/{order_id}`: Update order priority, clinical indication, or status.
- `POST /api/v1/orders/{order_id}/results`: Ingest/record diagnostic result.
- `GET /api/v1/patients/{patient_id}/diagnostic-results`: List diagnostic results with critical flag filtering.
- `GET /api/v1/diagnostic-results/{result_id}`: Get diagnostic result details.
- `POST /api/v1/diagnostic-results/{result_id}/review`: Clinician review and closed-loop result signoff.
- `POST /api/v1/tasks/patients/{patient_id}/orders/verify`: Async background order verification.
- `POST /api/v1/tasks/orders/{order_id}/results/ingest`: Async background diagnostic result processing.

### 6. Frontend Workspace (`OrdersWorkspace.tsx`)
- Integrated in `DashboardPage.tsx` under tab `📦 Orders & Diagnostics`.
- Sub-tabs:
  1. `📋 Clinical Orders (CPOE)`: Order status boards, priority badges (`STAT`, `URGENT`, `ROUTINE`), category filtering, AI order bundle generator modal, pre-order conflict warnings.
  2. `🔬 Diagnostic Results & Panic Lab Feed`: Real-time result grid, high/low/panic badges, reference range visualizations, multi-parameter lab panel viewer, and one-click closed-loop signoff modal.

---

## Proposed Changes

### Database Layer
#### [NEW] [0015_clinical_orders_and_diagnostic_results.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/alembic/versions/0015_clinical_orders_and_diagnostic_results.py)
- Creates `clinical_orders` and `diagnostic_results` tables, foreign keys, indexes, and constraints.

#### [NEW] [order.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/order.py)
- SQLAlchemy ORM models `ClinicalOrder` and `DiagnosticResult`.

#### [MODIFY] [__init__.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/models/__init__.py)
- Export `ClinicalOrder` and `DiagnosticResult`.

---

### Schemas Layer
#### [NEW] [order.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/order.py)
- Enums: `OrderCategory`, `OrderPriority`, `OrderStatus`, `DiagnosticResultStatus`, `AbnormalFlag`.
- Pydantic schemas for order creation, update, response, result ingestion, result review, and order bundle recommendations.

#### [MODIFY] [task.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/task.py)
- Add `ORDER_VERIFICATION` and `RESULT_INGESTION` to `BackgroundTaskType`.

#### [MODIFY] [fhir.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/fhir.py)
- Add `SERVICE_REQUEST` and `DIAGNOSTIC_REPORT` to `FHIRResourceType`.
- Add `FHIRServiceRequest` and `FHIRDiagnosticReport` schemas.

#### [MODIFY] [__init__.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/schemas/__init__.py)
- Export order and diagnostic result schemas.

---

### AI & Service Layer
#### [NEW] [order_provider.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/ai/order_provider.py)
- Abstract base provider and deterministic `MockOrderVerificationProvider` for clinical order sets, duplicate checking, and panic value evaluation.

#### [NEW] [order_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/order_service.py)
- CPOE order management, result ingestion, panic alert propagation, clinician signoffs, and background task worker functions.

#### [MODIFY] [fhir_mapper_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/fhir_mapper_service.py)
- Add `FHIRServiceRequestMapper` and `FHIRDiagnosticReportMapper`.

#### [MODIFY] [fhir_export_service.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/services/fhir_export_service.py)
- Add `export_order_as_fhir_service_request` and `export_result_as_fhir_diagnostic_report`.

---

### API Layer
#### [NEW] [orders.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/endpoints/orders.py)
- REST router for CPOE orders and diagnostic results.

#### [MODIFY] [fhir.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/endpoints/fhir.py)
- Add `GET /ServiceRequest/{order_id}` and `GET /DiagnosticReport/{result_id}` endpoints.

#### [MODIFY] [api.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/api.py)
- Register `orders.router`.

---

### Frontend Layer
#### [MODIFY] [index.ts](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/types/index.ts)
- Add TypeScript interfaces and enums for orders and diagnostic results.

#### [MODIFY] [client.ts](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/api/client.ts)
- Add `ordersApi` client methods.

#### [NEW] [OrdersWorkspace.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/components/orders/OrdersWorkspace.tsx)
- CPOE order entry interface, order set bundle picker, pending orders tracker, critical results feed, and result review signoff modal.

#### [MODIFY] [DashboardPage.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/pages/DashboardPage.tsx)
- Add `📦 Orders & Diagnostics` tab and render `OrdersWorkspace`.

---

### Testing & Documentation
#### [NEW] [test_orders_and_results.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/tests/test_orders_and_results.py)
- Test order creation, duplicate check, bundle synthesis, result ingestion, panic value detection, closed-loop signoff, background workers, FHIR export, and RBAC isolation.

#### [NEW] [orders.test.tsx](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/frontend/src/test/orders.test.tsx)
- Test order workspace rendering, order bundle synthesis modal, and diagnostic result signoff.

#### [NEW] [phase_9_0_13.md](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/docs/phase_9_0_13.md)
- Complete technical documentation for Phase 9.0.13.

#### [MODIFY] [README.md](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/README.md)
- Update roadmap with Phase 9.0.13.

---

## Verification Plan

### Automated Testing
- Backend focused: `.\backend\.venv\Scripts\pytest.exe backend\tests\test_orders_and_results.py -v`
- Full backend regression: `.\backend\.venv\Scripts\pytest.exe backend\tests -q` (Target: 362+ passing)
- Frontend unit tests: `npm.cmd test -- --run` (Target: 28+ passing across 11 suites)
- Frontend production build: `npm.cmd run build` in `frontend/`
- Alembic migration 0015 SQL validation: `.\backend\.venv\Scripts\alembic.exe -c backend\alembic.ini upgrade head --sql`
- Clean git diff check: `git diff --cached --check`

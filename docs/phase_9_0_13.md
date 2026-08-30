# Phase 9.0.13 — Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking

## Overview
Phase 9.0.13 establishes structured Computerized Physician Order Entry (CPOE) and closed-loop diagnostic result tracking in MediGen-AI. In inpatient and ambulatory healthcare, clinical orders (laboratory panels, diagnostic imaging, inpatient medications, nursing interventions, and consults) drive care execution. This phase ensures automated duplicate order verification, AI-suggested protocol bundles (Sepsis, Chest Pain/ACS, DKA, General Inpatient Admission), automated panic/critical value detection, and mandatory clinician review/signoff.

---

## Key Capabilities

### 1. Computerized Physician Order Entry (CPOE)
- **Order Categories**: `laboratory`, `imaging`, `medication`, `nursing`, `consultation`.
- **Order Priorities**: `routine`, `urgent`, `stat`.
- **Order Lifecycle**: `draft` $\rightarrow$ `placed` $\rightarrow$ `in_progress` $\rightarrow$ `completed` / `cancelled`.
- **Pre-Order Safety & Redundancy Guard**:
  - Automatically identifies duplicate orders placed within the preceding 24–48 hours.
  - Automatically flags clinical contraindications (e.g. IV contrast in patients with acute kidney injury or chronic renal impairment).

### 2. AI-Assisted Clinical Order Set Protocols
- Deterministic 100% offline heuristic engine supporting standardized protocol bundles:
  - **Chest Pain / Acute Coronary Syndrome (ACS)**: STAT High-Sensitivity Troponin I, Baseline BMP, CBC, 2-View Chest X-Ray.
  - **Sepsis Early Intervention Bundle**: STAT Serum Lactate, Blood Cultures $\times 2$, CBC with Differential, CMP.
  - **Diabetic Ketoacidosis (DKA) Protocol**: STAT BMP (electrolytes & anion gap), Venous Blood Gas, Quantitative Beta-Hydroxybutyrate, HbA1c.
  - **General Clinical Inpatient Admission Set**: Baseline CBC, CMP, Urinalysis.

### 3. Closed-Loop Diagnostic Results & Panic Lab Tracking
- Ingestion of structured numerical and narrative diagnostic findings.
- Automated abnormal flag classification: `normal`, `abnormal_low`, `abnormal_high`, `panic_critical`.
- Automatic triggering of immediate `CRITICAL` severity `ClinicalAlert` events upon panic threshold detection (e.g., Potassium $<2.8$ or $>6.2$ mEq/L, Troponin $\ge 0.04$ ng/mL, Platelets $<30 \times 10^3/\mu\text{L}$).
- Mandatory clinician review and signoff with timestamped verification to eliminate lost-in-the-system diagnostic delays.

### 4. FHIR R4 Interoperability
- **`FHIRServiceRequest`**: Standard LOINC/SNOMED coding, priority mapping, subject and practitioner references.
- **`FHIRDiagnosticReport`**: Category `LAB`, LOINC test identification, observation linkages, and abnormal findings summary.

---

## API Reference

### Orders & CPOE
- `POST /api/v1/patients/{patient_id}/orders`: Place new clinical order.
- `POST /api/v1/patients/{patient_id}/orders/suggest-bundle`: AI order set recommendation.
- `GET /api/v1/patients/{patient_id}/orders`: List clinical orders with status and category filtering.
- `GET /api/v1/orders/{order_id}`: Get full order details and linked results.
- `PATCH /api/v1/orders/{order_id}`: Update order priority, status, or details.

### Diagnostic Results & Signoffs
- `POST /api/v1/orders/{order_id}/results`: Ingest/record diagnostic result.
- `GET /api/v1/patients/{patient_id}/diagnostic-results`: List patient diagnostic results with abnormal flag filtering.
- `GET /api/v1/diagnostic-results/{result_id}`: Get diagnostic result details.
- `POST /api/v1/diagnostic-results/{result_id}/review`: Clinician review and closed-loop result signoff.

### Background Tasks & FHIR Interoperability
- `POST /api/v1/tasks/patients/{patient_id}/orders/{order_id}/verify`: Background order re-verification.
- `POST /api/v1/tasks/orders/{order_id}/results/ingest`: Background lab result feed processing.
- `GET /api/v1/fhir/ServiceRequest/{order_id}`: Export order as FHIR R4 ServiceRequest.
- `GET /api/v1/fhir/DiagnosticReport/{result_id}`: Export diagnostic result as FHIR R4 DiagnosticReport.

---

## Database Architecture (`0015_clinical_orders_and_diagnostic_results`)
- `clinical_orders`: Table storing CPOE orders, status lifecycle, safety flags, and clinician linkages.
- `diagnostic_results`: Table storing test codes (LOINC), numeric values, reference ranges, panic thresholds, abnormal flags, and clinician signoff timestamps.

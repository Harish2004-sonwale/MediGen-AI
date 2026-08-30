# Phase 9.0.15 — Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols

## Overview
Phase 9.0.15 establishes a production-grade Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs), and Telehealth platform that extends the core clinical workflows of MediGen-AI.

It connects continuous physiological telemetry ingestion (blood pressure cuffs, glucometers, pulse oximeters, weight scales, thermometers) with deterministic multi-tier threshold monitoring, automated escalation to CDS alerts and care plans, standardized PROM survey scoring (PHQ-9, GAD-7, PROMIS-10), and virtual consultation briefings.

---

## Key Capabilities

### 1. Longitudinal RPM Programs & Connected Medical Devices
- **`RPMProgram`**: Structured enrollment linking patient chronic conditions (e.g. Essential Hypertension, Type 2 Diabetes, CHF) to specific cadences and measurable clinical goals.
- **`RPMDevice`**: Wearable and peripheral device registration tracking device types (`blood_pressure_cuff`, `glucometer`, `pulse_oximeter`, `weight_scale`, `thermometer`), manufacturers, serial numbers, operational statuses, and synchronization timestamps.

### 2. Deterministic Physiological Telemetry & Drift Detection
- Ingests vital telemetry across multiple connectivity sources (`bluetooth_sync`, `cellular_gateway`, `manual_entry`, `api_integration`).
- Multi-tier classification: Evaluates readings into `normal`, `abnormal`, and `critical` states.
- Repeated drift evaluation: Automatically flags persistent out-of-range drift ($\ge 2$ consecutive abnormal readings) to identify subtle physiological deterioration before acute emergencies arise.

### 3. Clinician-in-the-Loop Automated Escalation Workflow
- **`RPMEscalationAlert`**: Automatically triggered when critical thresholds or repeated abnormal drift occurs.
- Seamless Care Coordination: Immediately creates an urgent `CareTask` attached to the patient's active `CarePlan` and issues a high-priority `ClinicalAlert`.
- Documented Resolution: Provides structured clinician acknowledgement and documented resolution workflows.

### 4. Standardized Patient-Reported Outcomes (PROMs)
- Pre-seeded standardized clinical surveys:
  - **`PROM-PHQ9`**: Patient Health Questionnaire (9-item depression assessment) with automated Question 9 suicidal ideation safety flag detection.
  - **`PROM-GAD7`**: Generalized Anxiety Disorder (7-item assessment).
  - **`PROM-PROMIS10`**: PROMIS Global Health (10-item physical and mental health assessment).
- Deterministic scoring, severity classification, and automated safety alert triggers.

### 5. Telehealth Protocols & AI Pre-Visit Briefings
- **`TelehealthSession`**: Virtual care consultation management supporting status lifecycle (`scheduled`, `waiting_room`, `in_progress`, `completed`, `cancelled`).
- Deterministic Pre-Visit Briefing: Automatically synthesizes a 30-day telemetry summary, latest PROM scores, and AI-curated key discussion points prior to the virtual visit.
- Post-Visit Documentation: Clinician consultation notes and follow-up care task dispatch.

### 6. FHIR R4 Interoperability
- **`FHIRDevice`**: Bi-directional mapping for registered connected medical devices.
- **`FHIRQuestionnaire`**: Standard FHIR R4 Questionnaire representation of PROM survey definitions.
- **`FHIRQuestionnaireResponse`**: Patient PROM submissions exported as FHIR R4 QuestionnaireResponse resources.

---

## API Reference

### RPM Programs & Devices
- `POST /api/v1/rpm/programs/enroll`: Enroll patient in an RPM program.
- `GET /api/v1/rpm/programs`: List RPM programs with patient isolation.
- `POST /api/v1/rpm/devices`: Register and assign a medical device.
- `GET /api/v1/rpm/devices`: List registered devices.

### Physiological Telemetry
- `POST /api/v1/rpm/observations`: Ingest continuous vital observation with automated threshold triage.
- `GET /api/v1/rpm/observations`: List telemetry stream with type and classification filters.
- `GET /api/v1/rpm/patients/{patient_id}/summary`: Aggregate 30-day telemetry, trend metrics, and adherence rates.

### Escalation Alerts
- `GET /api/v1/rpm/alerts`: List RPM escalation alerts.
- `POST /api/v1/rpm/alerts/{alert_id}/acknowledge`: Clinician acknowledgement of alert.
- `POST /api/v1/rpm/alerts/{alert_id}/resolve`: Document clinical resolution and dispatch follow-up care task.

### Patient-Reported Outcomes (PROMs)
- `GET /api/v1/rpm/proms/definitions`: List validated survey definitions.
- `POST /api/v1/rpm/proms/responses`: Submit survey responses with deterministic scoring and safety check.
- `GET /api/v1/rpm/proms/responses`: List historical survey submissions with patient isolation.

### Telehealth & Virtual Visits
- `POST /api/v1/rpm/telehealth/sessions`: Schedule virtual visit and generate pre-visit briefing.
- `GET /api/v1/rpm/telehealth/sessions`: List scheduled virtual visits.
- `GET /api/v1/rpm/telehealth/sessions/{session_id}`: Retrieve session briefing and clinical notes.
- `PATCH /api/v1/rpm/telehealth/sessions/{session_id}`: Progress visit status and document post-visit actions.

### FHIR R4 Endpoints
- `GET /api/v1/fhir/Device/{device_id}`: Export device as FHIR R4 Device.
- `GET /api/v1/fhir/Questionnaire/{prom_id}`: Export survey definition as FHIR R4 Questionnaire.
- `GET /api/v1/fhir/QuestionnaireResponse/{response_id}`: Export survey submission as FHIR R4 QuestionnaireResponse.

---

## Verification Summary
- **Backend Test Suite**: 8/8 new integration tests passed; **377/377 total test suite passed**.
- **Frontend Test Suite**: 4/4 new component tests passed; **36/36 total test suite passed** across 13 test suites.
- **Frontend Production Build**: Clean TypeScript compilation and Vite build (`dist/assets/index-*.js`).
- **Database Migration**: Verified `0017_rpm_proms_telehealth.py` with `alembic upgrade head --sql`.

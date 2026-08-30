# Phase 9.0.15 Implementation Plan: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols

## 1. Executive Summary & Objective
Phase 9.0.15 introduces an enterprise-grade Remote Patient Monitoring (RPM), Patient-Reported Outcome Measures (PROMs), and Virtual Care / Telehealth Protocol Engine to the MediGen-AI platform.

The engine establishes a continuous, out-of-hospital care delivery paradigm that connects:
1. **Remote Patient Monitoring (RPM)**: Continuous and periodic physiological measurement ingestion (Blood Pressure, Heart Rate, SpO2, Temperature, Weight, Blood Glucose) from connected medical devices and wearables with deterministic multi-tier threshold evaluation (normal, abnormal, critical, repeated drift).
2. **Automated Escalation Workflows**: Immediate generation of CDS alerts and auto-creation of urgent `CareTask` remediation items in patient `CarePlan`s upon critical/repeated threshold violations.
3. **Standardized Patient-Reported Outcomes (PROMs)**: Standardized questionnaire framework (PHQ-9 for depression screening, GAD-7 for generalized anxiety, PROMIS-10 / generic functional assessments) with automated multi-domain scoring, severity interpretation, longitudinal trend tracking, and clinician review.
4. **Telehealth & Virtual Care Protocols**: Structured pre-visit automated clinical synthesis (RPM telemetry summaries + recent PROM outcomes), telehealth session lifecycle (`scheduled` $\rightarrow$ `in_progress` $\rightarrow$ `completed` / `no_show` / `cancelled`), video/audio consultation metadata, and automated post-visit follow-up task generation.
5. **FHIR R4 Interoperability**: Bi-directional mapping and export of `Device`, `Observation` (telemetry/survey), `Questionnaire`, and `QuestionnaireResponse`.
6. **Strict RBAC & Patient Isolation**: Patient role accesses only their own assigned devices, telemetry streams, questionnaires, and virtual sessions; Clinician and Admin roles access population telemetry analytics and escalation queues.

---

## 2. Architecture & Relational Database Design

### Alembic Migration: `0017_rpm_proms_telehealth.py` (down_revision: `0016_clinical_quality_measures_and_compliance`)

### Models in `backend/app/models/rpm.py`:
1. **`RPMProgram`** (`rpm_programs`):
   - `id`, `program_id` (e.g. `RPM-PROG-20260829-XXXX`), `patient_id` (FK `patients.id`), `enrolled_by_user_id` (FK `users.id`), `condition_name`, `program_name`, `status` (`active`, `paused`, `completed`, `discharged`), `target_cadence_days`, `clinical_goals`, `created_at`, `updated_at`.
2. **`RPMDevice`** (`rpm_devices`):
   - `id`, `device_id` (e.g. `DEV-20260829-XXXX`), `patient_id` (FK `patients.id`), `device_type` (`blood_pressure_cuff`, `pulse_oximeter`, `glucometer`, `smart_scale`, `wearable_sensor`, `thermometer`), `manufacturer`, `model_number`, `serial_number`, `status` (`active`, `inactive`, `maintenance`, `revoked`), `supported_measurements_json`, `last_sync_at`, `created_at`.
3. **`RPMObservation`** (`rpm_observations`):
   - `id`, `observation_id` (e.g. `ROBS-20260829-XXXX`), `patient_id` (FK `patients.id`), `device_id` (FK `rpm_devices.id`), `observation_type` (`systolic_bp`, `diastolic_bp`, `heart_rate`, `spo2_percent`, `glucose_mgdl`, `weight_kg`, `temperature_c`), `numeric_value`, `unit_of_measure`, `classification` (`normal`, `abnormal`, `critical`), `measured_at`, `ingested_at`, `source_type` (`bluetooth_sync`, `cellular_gateway`, `patient_manual_entry`), `is_acknowledged`, `raw_payload_json`.
4. **`RPMThresholdRule`** (`rpm_threshold_rules`):
   - `id`, `rule_id` (e.g. `RULE-20260829-XXXX`), `patient_id` (FK `patients.id`, nullable for global defaults), `observation_type`, `normal_min`, `normal_max`, `critical_low`, `critical_high`, `consecutive_readings_trigger` (e.g. 2 repeated abnormal readings), `is_active`, `created_at`.
5. **`RPMEscalationAlert`** (`rpm_escalation_alerts`):
   - `id`, `alert_id` (e.g. `RESC-20260829-XXXX`), `patient_id` (FK `patients.id`), `observation_id` (FK `rpm_observations.id`), `severity` (`MODERATE`, `HIGH`, `CRITICAL`), `status` (`open`, `acknowledged`, `resolved`, `dismissed`), `escalation_reason`, `clinical_action_taken`, `linked_care_task_id` (FK `care_tasks.id`), `acknowledged_by_user_id`, `resolved_by_user_id`, `created_at`, `acknowledged_at`, `resolved_at`.
6. **`PROMDefinition`** (`prom_definitions`):
   - `id`, `prom_id` (e.g. `PROM-PHQ9`, `PROM-GAD7`, `PROM-PROMIS10`), `title`, `domain` (`mental_health`, `functional_status`, `symptom_burden`, `quality_of_life`), `version`, `questions_json` (array of `{id, prompt, options: [{label, score}]}`), `scoring_method` (`sum_total`, `mean`, `standardized_t_score`), `interpretation_ranges_json` (array of `{min, max, severity, clinical_summary}`), `is_active`, `created_at`.
7. **`PROMResponse`** (`prom_responses`):
   - `id`, `response_id` (e.g. `PRES-20260829-XXXX`), `prom_id` (FK `prom_definitions.id`), `patient_id` (FK `patients.id`), `encounter_id` (FK `encounters.id`, nullable), `answers_json`, `calculated_score`, `severity_interpretation`, `clinical_notes`, `completed_at`, `reviewed_by_user_id`, `reviewed_at`.
8. **`TelehealthSession`** (`telehealth_sessions`):
   - `id`, `session_id` (e.g. `TELE-20260829-XXXX`), `patient_id` (FK `patients.id`), `clinician_user_id` (FK `users.id`), `appointment_id` (FK `appointments.id`, nullable), `encounter_id` (FK `encounters.id`, nullable), `status` (`scheduled`, `waiting_room`, `in_progress`, `completed`, `cancelled`, `no_show`), `scheduled_start`, `actual_start`, `actual_end`, `visit_reason`, `pre_visit_rpm_summary_json`, `pre_visit_prom_summary_json`, `session_notes`, `followup_instructions`, `created_at`, `updated_at`.

---

## 3. Deterministic AI Provider & Services

### `backend/app/ai/rpm_provider.py`:
- `BaseRPMProvider` and `MockRPMProvider`:
  - Deterministic evaluation of RPM observations against configured normal/abnormal/critical thresholds.
  - Identification of repeated abnormal trends (e.g. systolic BP $>140\text{ mmHg}$ in $\ge 2$ consecutive readings within 48h).
  - Scoring algorithms for standard PROMs (PHQ-9 depression screening with suicidal ideation alert flags, GAD-7 anxiety scoring, PROMIS-10 Global Health).
  - Synthesis of pre-visit telehealth clinical briefing combining active RPM telemetry and latest PROM outcome scores.

### `backend/app/services/rpm_service.py`:
- Enrollment & Device Assignment: Register and bind biometric devices to patient profiles.
- Telemetry Ingestion & Real-Time Evaluation:
  - Validates observations, evaluates threshold rules, detects repeated drift, and persists records.
  - Automatically raises `RPMEscalationAlert` and attaches `CareTask` to active `CarePlan` upon critical readings.
- PROM Survey Management:
  - Seeds default PROM templates (PHQ-9, GAD-7, PROMIS-10).
  - Submits survey answers, executes deterministic scoring, and saves interpreted responses.
- Telehealth Session Orchestration:
  - Generates pre-visit clinical summaries aggregating recent RPM vitals and PROM scores.
  - Manages session lifecycle (`scheduled` $\rightarrow$ `in_progress` $\rightarrow$ `completed`), with optional encounter and follow-up `CareTask` creation.

---

## 4. FHIR R4 Interoperability

- `FHIRDevice`: Resource mapping for registered RPM devices (type, manufacturer, serial number, patient subject).
- `FHIRObservation`: Observation resource for remote telemetry readings and PROM scores with standard LOINC codes.
- `FHIRQuestionnaire`: Questionnaire resource definition.
- `FHIRQuestionnaireResponse`: QuestionnaireResponse resource capturing patient submissions.

Endpoints:
- `GET /api/v1/fhir/Device/{device_id}`
- `GET /api/v1/fhir/Questionnaire/{prom_id}`
- `GET /api/v1/fhir/QuestionnaireResponse/{response_id}`

---

## 5. REST API Layer (`backend/app/api/v1/endpoints/rpm.py`)

- **RPM Programs & Devices**:
  - `POST /api/v1/rpm/programs/enroll`: Enroll patient in RPM program.
  - `GET /api/v1/rpm/programs`: List RPM programs.
  - `POST /api/v1/rpm/devices`: Register and assign device to patient.
  - `GET /api/v1/rpm/devices`: List devices.
- **RPM Telemetry & Observations**:
  - `POST /api/v1/rpm/observations`: Ingest biometric observation with threshold evaluation.
  - `GET /api/v1/rpm/patients/{patient_id}/observations`: List observations with classification filtering.
  - `GET /api/v1/rpm/patients/{patient_id}/summary`: Telemetry metrics summary (trends, averages, violations).
- **RPM Escalation Alerts**:
  - `GET /api/v1/rpm/alerts`: List escalation alerts.
  - `POST /api/v1/rpm/alerts/{alert_id}/acknowledge`: Clinician acknowledgment.
  - `POST /api/v1/rpm/alerts/{alert_id}/resolve`: Alert resolution with clinical documentation.
- **Patient-Reported Outcomes (PROMs)**:
  - `GET /api/v1/rpm/proms/definitions`: List available PROM questionnaire templates.
  - `POST /api/v1/rpm/proms/responses`: Submit patient PROM questionnaire response.
  - `GET /api/v1/rpm/patients/{patient_id}/proms/responses`: List patient PROM history.
- **Telehealth & Virtual Care**:
  - `POST /api/v1/rpm/telehealth/sessions`: Schedule telehealth session.
  - `GET /api/v1/rpm/telehealth/sessions`: List telehealth sessions.
  - `GET /api/v1/rpm/telehealth/sessions/{session_id}`: Retrieve session details and pre-visit clinical briefing.
  - `PATCH /api/v1/rpm/telehealth/sessions/{session_id}`: Update session status, notes, and follow-ups.

---

## 6. Frontend Workspace (`frontend/src/components/rpm/RPMWorkspace.tsx`)

- **Clinician & Patient Dual View Modes**:
  - Clinician Mode: Population monitoring dashboard, active RPM device statuses, real-time telemetry observation logs with abnormal/critical badges, open escalation queue with "Acknowledge" & "Create Care Task", PROM response trends, and Telehealth session manager with pre-visit clinical briefing drawer.
  - Patient Mode: Patient-facing device status, recent vitals graph/timeline, interactive PROM survey completion modal, and scheduled telehealth consultation cards with instructions.
- Connected to `DashboardPage.tsx` under workspace tab `📡 Remote Monitoring & Telehealth`.

---

## 7. Testing & Verification Strategy

1. **Backend Tests (`backend/tests/test_rpm_proms_telehealth.py`)**:
   - Device registration and patient assignment.
   - Observation ingestion, normal vs abnormal vs critical threshold classifications.
   - Repeated abnormal measurement detection and escalation alert triggering.
   - Clinician alert acknowledgment and resolution.
   - PROM questionnaire completion, deterministic PHQ-9 / GAD-7 scoring, and interpretation.
   - Telehealth session scheduling, pre-visit summary compilation, status progression, and follow-up `CareTask` creation.
   - Strict RBAC and cross-patient isolation.
   - FHIR Device, Questionnaire, and QuestionnaireResponse exports.
   - Async background task worker dispatch.
2. **Full Regression Suites**:
   - Pytest full backend regression.
   - Vitest frontend test suites.
   - Production bundle compilation (`npm run build`).
   - Alembic migration dry-run (`alembic upgrade head --sql`).

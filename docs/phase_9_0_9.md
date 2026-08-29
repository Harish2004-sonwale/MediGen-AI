# Phase 9.0.9 — Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion

## Overview
Phase 9.0.9 establishes a real-time vital telemetry ingestion and Clinical Decision Support (CDS) alerting architecture for MediGen AI. It integrates structured multi-parameter physiological measurements (Heart Rate, Blood Pressure, Respiratory Rate, Body Temperature, SpO2, and Weight) with an automated deterministic rule engine that detects critical clinical thresholds, enforces alarm-fatigue debouncing, and records clinician review and dismissal audit trails.

---

## 1. Key Architectural Components

### 1.1 Vital Telemetry Ingestion (`VitalTelemetry`)
- **Table**: `vital_telemetry` (Alembic migration `0011_vitals_and_clinical_alerts.py`)
- **Identifiers**: `VIT-YYYYMMDD-XXXXXX`
- **Physiological Fields**:
  - `heart_rate` (bpm)
  - `systolic_bp` & `diastolic_bp` (mmHg)
  - `respiratory_rate` (breaths/min)
  - `temperature_c` (Celsius, automatically converted from Fahrenheit if >45°C)
  - `spo2_percent` (SpO2 percentage)
  - `weight_kg` (kg)
- **Provenance**: `device_id`, `source` (`bedside_monitor`, `simulator`, `manual_entry`), `measured_at`.

### 1.2 Clinical Decision Support Alerting (`ClinicalAlert`)
- **Table**: `clinical_alerts` (Alembic migration `0011_vitals_and_clinical_alerts.py`)
- **Identifiers**: `ALT-YYYYMMDD-XXXXXX`
- **Severity Tiers**: `INFO`, `LOW`, `MODERATE`, `HIGH`, `CRITICAL`.
- **Lifecycle States**:
  - `active`: Newly raised alert requiring clinician review.
  - `acknowledged`: Clinician has reviewed and taken clinical note.
  - `dismissed`: Clinician has dismissed alert with a mandatory clinical justification.
  - `resolved`: Underlying parameter returned to normal baseline.

### 1.3 Deterministic Rule Engine & Alarm-Fatigue Debouncing
- **Rule Thresholds**:
  - **Hypoxia**: SpO2 < 90% (`CRITICAL`), SpO2 90–93% (`HIGH`).
  - **Tachycardia**: HR > 140 bpm (`CRITICAL`), HR 101–140 bpm (`MODERATE`).
  - **Bradycardia**: HR < 40 bpm (`CRITICAL`), HR 40–49 bpm (`HIGH`).
  - **Hypertensive Crisis**: SBP >= 180 or DBP >= 120 mmHg (`CRITICAL`).
  - **Hypotension**: SBP < 85 or DBP < 50 mmHg (`CRITICAL`).
  - **Hyperthermia**: Temp >= 39.5°C (`HIGH`).
- **30-Minute Debouncing**: Suppresses redundant alerts for the same patient and alert type within a 30-minute window while incrementing `recurrence_count` and updating the latest triggering snapshot.

### 1.4 Offline Deterministic Telemetry Simulator
- Built-in simulation profiles (`NORMAL`, `HYPOXIC`, `HYPERTENSIVE_CRISIS`, `TACHYCARDIC`, `BRADYCARDIC`) for automated testing and UI demonstration with zero external API dependencies.

---

## 2. API Endpoints

| Method | Endpoint | Access Role | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients/{patient_id}/vitals` | Doctor, Staff, Admin | Ingest vital reading and evaluate CDS alerts |
| `GET` | `/api/v1/patients/{patient_id}/vitals` | Authenticated / Isolated | List historical vital telemetry readings |
| `GET` | `/api/v1/patients/{patient_id}/vitals/latest` | Authenticated / Isolated | Retrieve latest vital telemetry snapshot |
| `POST` | `/api/v1/patients/{patient_id}/vitals/simulate` | Doctor, Staff, Admin | Ingest preset simulated vital reading |
| `GET` | `/api/v1/patients/{patient_id}/alerts` | Authenticated / Isolated | List active/historical CDS alerts |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Doctor, Staff, Admin | Clinician acknowledgement of active alert |
| `POST` | `/api/v1/alerts/{alert_id}/dismiss` | Doctor, Staff, Admin | Clinician dismissal with mandatory reason |
| `GET` | `/api/v1/alerts/{alert_id}` | Authenticated / Isolated | Retrieve alert details and parameter snapshot |

---

## 3. Frontend Telemetry & Alerting Workspace
- **Component**: `VitalTelemetryWorkspace.tsx` (`frontend/src/components/telemetry/VitalTelemetryWorkspace.tsx`)
- **Features**:
  - Real-time parameter metric cards with color-coded status badges.
  - Interactive CDS alert stack with acknowledgement and dismissal workflows.
  - Telemetry simulator controls.
  - Historical reading table with device provenance.
  - Assistive clinical decision support disclaimer.

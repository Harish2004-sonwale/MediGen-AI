# Phase 9.0.17 Implementation Plan — Advanced Clinical AI Agents & Autonomous Care Coordination

## Executive Summary
Phase 9.0.17 builds a multi-agent clinical coordination and synthesis layer. It integrates MediGen-AI's completed modules (encounters, vitals, CDS alerts, care plans, orders/results, quality gaps, RPM/PROMs, transitions/discharge, and trials/genomics) through specialized assistive AI agents governed by strict clinician-in-the-loop approval gates, cryptographic audit provenance, and zero autonomous prescription/ordering constraints.

---

## 1. Multi-Agent Coordination Architecture

### Specialized Sub-Agents:
1. **Clinical Context Aggregator Agent (`clinical_context`)**: Aggregates longitudinal encounters, diagnoses, medications, allergies, vitals, labs, alerts, care plans, RPM telemetry, quality gaps, transitions, and genomic findings into a structured context snapshot with staleness tracking.
2. **Risk Surveillance Agent (`risk_surveillance`)**: Deterministically assesses vital trends, severe CDS alerts, high RPM drift, and deteriorating longitudinal risk metrics.
3. **Care Coordination Agent (`care_coordination`)**: Detects overdue care tasks, missing follow-ups, and unscheduled protocol reviews; routes actions to assigned clinical roles.
4. **Diagnostic Follow-Up Agent (`diagnostic_followup`)**: Tracks open-loop diagnostic orders and critical results lacking documented clinician acknowledgement or care follow-up.
5. **Medication Safety Agent (`medication_safety`)**: Detects drug duplications, drug-allergy warnings, and medication reconciliation gaps; strictly generates recommendations without altering prescriptions.
6. **Quality Gap Agent (`quality_gap`)**: Links open HEDIS/MIPS clinical quality measure gaps to actionable care outreach tasks.
7. **RPM / Telehealth Agent (`rpm_telehealth`)**: Consumes persistent vital drift and high-severity PROM responses (such as PHQ-9 suicidal ideation safety flags) and recommends clinician telehealth consultation sessions.
8. **Transition & Discharge Agent (`transition_discharge`)**: Monitors unresolved 30-day readmission risks, pending handoff items, and post-discharge medication reconciliation tasks.
9. **Trial & Precision Oncology Agent (`trial_genomics`)**: Evaluates potential clinical trial matches and actionable targeted therapies for oncologist review.
10. **Master Orchestrator / Supervisor Agent (`master_orchestrator`)**: Coordinates the specialized agents, synthesizes a prioritized care coordination plan, enforces human-in-the-loop action classification, computes SHA-256 provenance hashes, and checks for stale context.

---

## 2. Safety & Human-in-the-Loop Governance

### Action Classes:
- **`READ_ONLY`**: Context aggregation and longitudinal timeline summarization.
- **`RECOMMENDATION`**: Low-risk informational suggestions displayed on clinical dashboard.
- **`CLINICIAN_APPROVAL_REQUIRED`**: Care coordination tasks, consultation bookings, or screening outreach.
- **`HIGH_RISK`**: Molecular oncology protocol reviews, medication review flags, or escalation workflows requiring formal clinician sign-off with credential verification.

### Safety Invariants:
- Agents **NEVER** autonomously prescribe, discontinue medication, place a clinical order, finalize a discharge, or override clinician decision.
- Anti-Prompt Injection: Clinical text (notes, complaints, observations) is treated as untrusted data and strictly sanitized before evaluation.
- Deterministic & Reproducible: Evaluated via `MockClinicalAgentProvider` and `BaseClinicalAgentProvider` with zero non-deterministic GPU/network dependencies.

---

## 3. Database Schema (Migration `0019_clinical_ai_agents_and_care_coordination.py`)

### Entities in `backend/app/models/agents.py`:
- **`ClinicalAgentDefinition`**: Registered clinical agents (agent_id, name, agent_type, description, version, is_active, capabilities_json, default_action_class).
- **`ClinicalAgentRun`**: Agent execution lifecycle tracking (run_id, agent_type, patient_id, initiated_by_user_id, status [`queued`, `running`, `waiting_for_approval`, `approved`, `executed`, `completed`, `failed`, `cancelled`], start_time, end_time, input_context_snapshot_json, context_hash, provenance_hash, overall_summary, error_message).
- **`ClinicalAgentRecommendation`**: Actionable recommendations (recommendation_id, run_id, patient_id, category, title, description, rationale, priority [`urgent`, `high`, `medium`, `low`], action_class [`READ_ONLY`, `RECOMMENDATION`, `CLINICIAN_APPROVAL_REQUIRED`, `HIGH_RISK`], suggested_action_type, suggested_action_payload_json, approval_status [`pending_review`, `approved`, `rejected`, `executed`, `expired`], reviewed_by_user_id, reviewed_at, review_notes, execution_status, executed_at, provenance_hash).
- **`AgentEvidenceReference`**: Traceability links (evidence_id, recommendation_id, entity_type [`encounter`, `observation`, `alert`, `care_task`, `order`, `result`, `rpm_observation`, `quality_gap`, `trial_match`], entity_identifier, title, excerpt, confidence_score).

---

## 4. API Endpoints (`backend/app/api/v1/endpoints/agents.py`)

- `POST /api/v1/agents/runs`: Trigger multi-agent clinical coordination run for a patient.
- `GET /api/v1/agents/runs`: List agent runs with patient, status, and agent_type filtering.
- `GET /api/v1/agents/runs/{run_id}`: Retrieve agent run detail with structured recommendations and evidence.
- `POST /api/v1/agents/runs/{run_id}/execute`: Execute approved recommendations for a run.
- `POST /api/v1/agents/recommendations/{recommendation_id}/approve`: Clinician approval with structured notes.
- `POST /api/v1/agents/recommendations/{recommendation_id}/reject`: Clinician rejection with clinical reason.
- `GET /api/v1/patients/{patient_id}/agent-runs`: List agent runs for active patient.
- `GET /api/v1/patients/{patient_id}/care-coordination`: Aggregate latest active recommendations and coordination status.
- `POST /api/v1/patients/{patient_id}/care-coordination/synthesize`: One-click multi-agent care coordination synthesis.

---

## 5. FHIR R4 Interoperability
- **`FHIRTask`**: Map agent recommendations requiring care task dispatch into standard FHIR R4 `Task` resources.
- **`FHIRCommunication`**: Map care coordination notifications and patient outreach proposals to standard FHIR R4 `Communication` resources.
- **`FHIRProvenance`**: Export cryptographic SHA-256 provenance records linking agent runs to source patient data.

---

## 6. Frontend Workspace
- **`frontend/src/components/agents/ClinicalAgentsWorkspace.tsx`**:
  - Sub-views: Active Coordination Hub, Agent Run History, Recommendation Approval Queue, Evidence & Provenance Inspector.
  - Interactive Action Approval dialogs with credential verification and clinical rationale documentation.
  - Multi-agent execution monitor with live progress indicators and human-in-the-loop disclaimer banners.
- Integrated into `DashboardPage.tsx` under `🤖 Clinical AI & Care Coordination` tab.

---

## 7. Verification Plan
- **Backend Test Suite**: `backend/tests/test_clinical_ai_agents.py` (lifecycle, context aggregation, deterministic mock reasoning, evidence references, recommendation approvals/rejections, anti-stale context protection, RBAC patient isolation, and FHIR export).
- **Frontend Test Suite**: `frontend/src/test/agents.test.tsx` (workspace tabs, approval workflows, evidence drawers, error states, and safety alerts).
- **Full Regression**: `pytest backend/tests -q`, `npm test -- --run`, `npm run build`, `alembic upgrade head --sql`.

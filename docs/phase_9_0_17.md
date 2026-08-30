# Phase 9.0.17 — Advanced Clinical AI Agents & Autonomous Care Coordination

## 1. Overview & Clinical Scope

Phase 9.0.17 introduces a **Clinician-Supervised Multi-Agent Autonomous Care Coordination Layer** to MediGen-AI. This layer orchestrates clinical intelligence across multiple clinical subsystems:
- Encounters, Clinical Notes, & SOAP Documentation
- Vital Telemetry & CDS Critical Alerts
- Computerized Physician Order Entry (CPOE) & Diagnostic Laboratory Results
- Clinical Quality Measures (CQMs, HEDIS/MIPS) & Care Gap Remediation
- Remote Patient Monitoring (RPM), Telehealth, & Patient-Reported Outcome Measures (PROMs)
- Clinical Transitions of Care & Hospital Discharge Planning
- Clinical Trials Matching & Biomarker Precision Oncology

### Core Safety Governance
- **ASSISTIVE Clinical AI**: Agents suggest, highlight, and draft recommendations. No AI agent may autonomously finalize clinical decisions, prescribe/discontinue medications, or order treatments without explicit clinician review.
- **Clinician Review Lifecycle**: Recommendations require explicit physician action (`pending_review` $\rightarrow$ `approved` / `rejected` / `overridden`).
- **Cryptographic Provenance**: Every evaluation payload, evidence reference, and recommendation generates a reproducible SHA-256 hash.
- **Prompt Injection Defense**: All clinical inputs, notes, complaints, and external text are sanitized and quarantined as untrusted data before agent evaluation.
- **FHIR R4 Interoperability**: Recommendations and multi-agent runs export natively as `FHIR R4 Task` and `FHIR R4 Provenance` resources.

---

## 2. Multi-Agent Topology & Specialized Subagents

The multi-agent system is structured with a **Master Orchestrator** and 10 domain-specific clinical agents:

| Agent Code | Domain Scope | Purpose & Clinical Responsibility | Execution Cadence | Action Class |
| :--- | :--- | :--- | :--- | :--- |
| `master_orchestrator` | `care_coordination` | Aggregates multi-agent insights into a prioritized, deduplicated clinical action plan. | `on_demand` | `RECOMMENDATION` |
| `clinical_context` | `clinical_context` | Synthesizes longitudinal clinical history across encounters, vitals, and diagnoses. | `event_driven` | `READ_ONLY` |
| `risk_surveillance` | `risk_surveillance` | Detects acute physiological deterioration, hypertensive crises, and unacknowledged CDS alerts. | `event_driven` | `HIGH_RISK` |
| `medication_safety` | `medication_safety` | Identifies duplicate active therapies, polypharmacy risks, and reconciliation needs. | `continuous` | `CLINICIAN_APPROVAL_REQUIRED` |
| `diagnostic_tracker`| `orders_diagnostics` | Closes diagnostic loops on unreviewed panic/critical lab results and unfulfilled urgent orders. | `event_driven` | `HIGH_RISK` |
| `quality_gap_agent` | `quality_compliance`| Detects open HEDIS/MIPS care gaps (e.g., HbA1c testing, screening) and recommends outreach tasks. | `scheduled` | `RECOMMENDATION` |
| `rpm_telehealth` | `rpm_telehealth` | Analyzes RPM vital drift and PROM behavioral health deterioration for telehealth referral. | `continuous` | `CLINICIAN_APPROVAL_REQUIRED` |
| `transitions_agent` | `transitions_care` | Audits discharge readiness, pending handoffs, and 30-day post-discharge safety monitoring. | `event_driven` | `RECOMMENDATION` |
| `trials_precision` | `trials_precision` | Matches oncologic biomarkers and trial eligibility criteria for experimental therapies. | `on_demand` | `RECOMMENDATION` |
| `care_plan_orchestrator` | `care_planning` | Aligns multidisciplinary care goals, barriers, and tasks across active chronic care plans. | `scheduled` | `RECOMMENDATION` |

---

## 3. Architecture & Data Model

### Database Tables (Alembic Migration `0019`)
1. `clinical_agent_definitions`: Registered agent specifications, domain scopes, capabilities, and versioning.
2. `clinical_agent_runs`: Immutable execution log per agent run, containing patient context snapshot, raw output payload, execution duration, and cryptographic SHA-256 provenance hash.
3. `clinical_agent_recommendations`: Actionable clinical suggestions with priority (`routine`, `medium`, `high`, `urgent`), action class (`READ_ONLY`, `RECOMMENDATION`, `CLINICIAN_APPROVAL_REQUIRED`, `HIGH_RISK`), and approval status (`pending_review`, `approved`, `rejected`, `overridden`).
4. `agent_evidence_references`: Granular evidence links tying recommendations back to specific encounters, vitals, orders, lab results, RPM observations, or alerts with confidence scores and excerpts.

---

## 4. REST API Endpoints

- `GET /api/v1/agents/definitions`: List all registered clinical agent definitions.
- `GET /api/v1/agents/runs`: List historical agent execution runs with filters.
- `GET /api/v1/agents/runs/{run_id}`: Retrieve detailed run execution with recommendations and provenance.
- `POST /api/v1/agents/runs/{agent_code}/execute`: Trigger isolated execution of a specific agent for a patient.
- `POST /api/v1/agents/patients/{patient_id}/care-coordination/synthesize`: Trigger full multi-agent care coordination synthesis.
- `GET /api/v1/agents/patients/{patient_id}/care-coordination`: Retrieve the most recent synthesized care coordination plan.
- `POST /api/v1/agents/recommendations/{recommendation_id}/approve`: Clinician review approval with optional clinical sign-off notes.
- `POST /api/v1/agents/recommendations/{recommendation_id}/reject`: Clinician review rejection with mandatory rationale notes.
- `POST /api/v1/agents/recommendations/{recommendation_id}/execute-action`: Dispatch approved recommendation into clinical action (e.g. Care Task creation).
- `POST /api/v1/agents/tasks/patients/{patient_id}/care-coordination`: Asynchronous background task execution.
- `GET /api/v1/fhir/Provenance/{run_id}`: FHIR R4 Provenance resource export.
- `GET /api/v1/fhir/AgentTask/{recommendation_id}`: FHIR R4 Task resource export.

---

## 5. Frontend Clinical AI Workspace

Accessible under the `🤖 Clinical AI & Care Coordination` tab in the Clinical Dashboard:
- **Clinician Supervision Banner**: Constant reminder of assistive AI boundaries and clinician sign-off mandates.
- **Active Patient Selector**: Dynamic switching across patient records.
- **Specialized Agent Registry**: Interactive cards showcasing domain scope, cadence, version, and active status for each agent.
- **Synthesis Action**: Single-click on-demand multi-agent synthesis with live progress and status notifications.
- **Prioritized Recommendations Feed**: Multi-filter view (by Priority, Action Class, and Review Status) displaying rationale, confidence metrics, SHA-256 provenance hashes, and direct evidence references.
- **Clinician Approval / Rejection Controls**: Integrated inline review actions with reason prompts.
- **Care Task Dispatch**: One-click action dispatch turning approved recommendations into structured Care Tasks.
- **FHIR R4 Export Modal**: Interactive JSON inspector for FHIR R4 Task and Provenance resources.

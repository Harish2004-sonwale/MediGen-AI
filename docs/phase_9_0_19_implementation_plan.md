# Phase 9.0.19 Implementation Plan — Clinical Security, Auditability, Consent & Compliance Governance

## 1. Executive Summary & Clinical Governance Policy
Phase 9.0.19 establishes an enterprise-grade clinical security, auditability, patient consent, data retention, and compliance governance framework for MediGen-AI.
- **Strict Clinical Governance & Safety**: This phase delivers governance and cybersecurity infrastructure. It does not perform autonomous diagnosis, clinical determinations, or unverified record deletions.
- **Immutable Audit Trail**: Tamper-evident cryptographic SHA-256 hash-chaining across all data access, export, authentication, and modification events. Operational and audit logs strictly prohibit raw Protected Health Information (PHI).
- **Patient Consent Sovereignty**: Patients retain full granular control over the use and disclosure of their medical, genomic, behavioral, and imaging records (opt-in/opt-out, purpose-of-use scoping, immediate effect on revocation).
- **Proactive Threat & Access Monitoring**: Deterministic anomaly detection flags unauthorized cross-patient scanning, repeated credential failures, bulk data exports, and policy breaches into a triaged Security Incident workflow.
- **Data Lifecycle & Legal Holds**: Enforces regulatory retention schedules (e.g. HIPAA 6-year audit trail, adult EHR 7-year retention) while strictly safeguarding clinical records against accidental deletion via enforceable Legal and Clinical Holds.

---

## 2. Architectural Data Models & Database Migration

### Migration Identifier: `0021_clinical_security_audit_consent_and_compliance.py`
Chained directly from `0020_medical_imaging_and_radiology_workflow.py`.

### 1. `clinical_audit_events` (Immutable Audit Trail)
- `id` (Integer, PK, autoincrement)
- `event_id` (String(64), unique, indexed, e.g. `AUD-YYYYMMDD-XXXXXXXX`)
- `timestamp` (DateTime(timezone=True), indexed, default=func.now())
- `user_id` (Integer, FK to `users.id`, nullable for unauthenticated attempts, indexed)
- `user_role` (String(32), indexed)
- `patient_id` (String(64), indexed, nullable for system-wide/admin operations)
- `action` (String(32), indexed — `CREATE`, `READ`, `UPDATE`, `DELETE`, `EXECUTE`, `EXPORT`, `LOGIN`, `LOGOUT`, `CONSENT_GRANT`, `CONSENT_REVOKE`, `SECURITY_ALERT`, `HOLD_APPLIED`, `HOLD_RELEASED`)
- `resource_type` (String(64), indexed — `Patient`, `Observation`, `DiagnosticReport`, `ImagingStudy`, `PatientConsent`, `GenomicProfile`, `User`, `ExportBundle`, `ClinicalNote`, `CarePlan`, `Order`, `Handoff`, `VitalReading`)
- `resource_id` (String(64), indexed, nullable)
- `ip_address` (String(45))
- `user_agent` (String(255))
- `purpose_of_use` (String(32), indexed — `TREATMENT`, `PAYMENT`, `OPERATIONS`, `RESEARCH`, `EMERGENCY_OVERRIDE`, `PATIENT_REQUEST`, `PUBLIC_HEALTH`)
- `outcome` (String(32), indexed — `SUCCESS`, `DENIED_FORBIDDEN`, `DENIED_NO_CONSENT`, `ERROR`, `WARNING`)
- `metadata_json` (JSON, sanitized non-PHI contextual metadata, modified fields, byte counts, filter criteria)
- `prev_record_hash` (String(64), SHA-256 hash of prior chronological audit record in the chain)
- `record_hash` (String(64), SHA-256 hash computed over `prev_record_hash + event_id + timestamp + user_id + patient_id + action + resource_type + resource_id + outcome`)

### 2. `patient_consents` (Granular Consent Directives)
- `id` (Integer, PK, autoincrement)
- `consent_id` (String(64), unique, indexed, e.g. `CNS-YYYYMMDD-XXXXXXXX`)
- `patient_id` (String(64), FK to `patients.patient_id`, indexed)
- `status` (String(32), indexed — `DRAFT`, `ACTIVE`, `REVOKED`, `EXPIRED`, `REJECTED`)
- `scope` (String(32), indexed — `ALL_RECORDS`, `GENOMICS_ONLY`, `RESEARCH_ONLY`, `BEHAVIORAL_HEALTH`, `IMAGING_ONLY`, `TREATMENT_CARE_TEAM`, `RESTRICT_EXPORT`, `THIRD_PARTY_DISCLOSURE`)
- `policy_rule` (String(16), indexed — `PERMIT`, `DENY`)
- `purpose_of_use` (String(32), indexed — `TREATMENT`, `RESEARCH`, `THIRD_PARTY_SHARING`, `MARKETING_PROHIBITED`, `EMERGENCY_OVERRIDE`)
- `data_category` (String(64), indexed, nullable — `GENOMICS`, `PSYCHIATRY`, `SUBSTANCE_USE`, `GENERAL_CLINICAL`, `IMAGING`, `TELEMETRY`)
- `actor_type` (String(32) — `CARE_TEAM`, `ORGANIZATION`, `RESEARCH_INSTITUTION`, `ALL_USERS`)
- `actor_reference` (String(128), nullable)
- `valid_from` (DateTime(timezone=True), nullable=False)
- `valid_to` (DateTime(timezone=True), nullable=True)
- `signed_by_patient` (Boolean, default=True)
- `signer_name` (String(128), nullable=False)
- `signer_relationship` (String(32), default="SELF" — `SELF`, `LEGAL_GUARDIAN`, `HEALTHCARE_PROXY`)
- `witness_or_clinician_id` (Integer, FK to `users.id`, nullable=True)
- `revoked_at` (DateTime(timezone=True), nullable=True)
- `revocation_reason` (String(255), nullable=True)
- `revoked_by_user_id` (Integer, FK to `users.id`, nullable=True)
- `digital_signature_hash` (String(64), SHA-256 provenance signature)
- `created_at`, `updated_at` (DateTime(timezone=True))

### 3. `security_incidents` (Threat & Anomaly Tracking)
- `id` (Integer, PK, autoincrement)
- `incident_id` (String(64), unique, indexed, e.g. `SEC-YYYYMMDD-XXXXXXXX`)
- `detected_at` (DateTime(timezone=True), indexed, default=func.now())
- `severity` (String(16), indexed — `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `status` (String(32), indexed — `OPEN`, `INVESTIGATING`, `RESOLVED`, `FALSE_POSITIVE`)
- `event_type` (String(64), indexed — `SUSPICIOUS_BULK_EXPORT`, `CROSS_PATIENT_ACCESS_ATTEMPT`, `REPEATED_AUTH_FAILURE`, `CONSENT_VIOLATION_ATTEMPT`, `AUDIT_TAMPER_DETECTED`, `RATE_LIMIT_EXCEEDED`, `UNAUTHORIZED_ROLE_ESCALATION`)
- `user_id` (Integer, FK to `users.id`, nullable=True, indexed)
- `patient_id` (String(64), nullable=True, indexed)
- `ip_address` (String(45), nullable=True)
- `description` (String(500), sanitized, zero-PHI incident summary)
- `evidence_metadata` (JSON, non-PHI telemetry snapshot, threshold triggers, timestamps)
- `assigned_to_user_id` (Integer, FK to `users.id`, nullable=True)
- `resolution_notes` (Text, nullable=True)
- `resolved_at` (DateTime(timezone=True), nullable=True)
- `resolved_by_user_id` (Integer, FK to `users.id`, nullable=True)
- `created_at`, `updated_at` (DateTime(timezone=True))

### 4. `data_retention_policies` (Regulatory Retention Schedules)
- `id` (Integer, PK, autoincrement)
- `policy_code` (String(32), unique, indexed — `ADULT_EHR_7YR`, `PEDIATRIC_EHR_21YR`, `AUDIT_LOG_6YR`, `IMAGING_10YR`, `GENOMIC_PERMANENT`, `RESEARCH_STUDY_ARCHIVE`)
- `data_category` (String(64), indexed)
- `retention_period_days` (Integer, -1 for permanent retention)
- `action_on_expiry` (String(32) — `ARCHIVE`, `ANONYMIZE`, `RESTRICTED_ACCESS`, `FLAG_REVIEW`)
- `description` (String(255))
- `is_active` (Boolean, default=True)
- `created_at`, `updated_at` (DateTime(timezone=True))

### 5. `legal_clinical_holds` (Immutable Preservation Overrides)
- `id` (Integer, PK, autoincrement)
- `hold_id` (String(64), unique, indexed, e.g. `HLD-YYYYMMDD-XXXXXXXX`)
- `patient_id` (String(64), nullable=True, indexed)
- `scope_category` (String(64), default="ALL_RECORDS")
- `reason` (String(255), nullable=False)
- `status` (String(32), indexed, default="ACTIVE" — `ACTIVE`, `RELEASED`)
- `placed_by_user_id` (Integer, FK to `users.id`, nullable=False)
- `placed_at` (DateTime(timezone=True), default=func.now())
- `released_by_user_id` (Integer, FK to `users.id`, nullable=True)
- `released_at` (DateTime(timezone=True), nullable=True)
- `notes` (Text, nullable=True)

---

## 3. Core Services & Engines

### 1. `AuditService` (`backend/app/services/audit_service.py`)
- Emits atomic, immutable `AuditEvent` records synchronously with database operations.
- Computes SHA-256 hash-chaining from previous audit event to ensure tamper evidence.
- Integrates tamper verification routine: re-walks audit event hash chain and flags any modified or removed blocks.
- Automatic non-PHI scrubbing filter on metadata.

### 2. `ConsentService` (`backend/app/services/consent_service.py`)
- Manages patient consent lifecycle (`grant_consent`, `revoke_consent`, `expire_consents`).
- Evaluates consent directives against requested clinical resources, purpose-of-use (`TREATMENT`, `RESEARCH`, `EXPORT`), and data categories (`GENOMICS`, `PSYCHIATRY`, `GENERAL`).
- Real-time revocation: revoking a consent immediately blocks matching export and non-emergency reads.

### 3. `SecurityMonitoringService` (`backend/app/services/security_monitoring_service.py`)
- Deterministic heuristic analysis over recent access patterns:
  - Detects rapid cross-patient access (> 3 unassigned patients within 5 minutes by non-admin).
  - Detects repeated authentication failures (> 5 within 10 minutes from single IP or user).
  - Detects excessive bulk export requests (> 3 bundle exports within 15 minutes).
  - Automatically spawns `SecurityIncident` entries with appropriate severity (`LOW` -> `CRITICAL`).

### 4. `ComplianceReportingService` (`backend/app/services/compliance_reporting_service.py`)
- Compiles structured compliance audit snapshots:
  - System Security & Tamper Integrity Score.
  - Audit event distribution by action, outcome, and resource.
  - Patient consent status & opt-out metrics.
  - Active Legal Holds and Retention Schedule compliance.
  - Security incident queue and resolution metrics.

---

## 4. REST API & FHIR R4 Interoperability

### Security & Audit Router (`backend/app/api/v1/endpoints/security.py`)
- `GET /api/v1/audit/events` (Filter by user, patient, action, outcome, date range; paginated)
- `GET /api/v1/audit/events/{event_id}`
- `POST /api/v1/audit/verify-integrity` (Executes SHA-256 hash chain verification)
- `POST /api/v1/patients/{patient_id}/consents` (Create/Grant patient consent directive)
- `GET /api/v1/patients/{patient_id}/consents` (List patient consent directives)
- `GET /api/v1/consents/{consent_id}`
- `POST /api/v1/consents/{consent_id}/revoke` (Immediate consent revocation)
- `POST /api/v1/consents/verify` (Explicit consent evaluation check)
- `GET /api/v1/security/incidents` (List security incidents)
- `GET /api/v1/security/incidents/{incident_id}`
- `PATCH /api/v1/security/incidents/{incident_id}` (Assign, resolve, or mark false positive)
- `POST /api/v1/security/scan` (Run proactive security anomaly analysis)
- `GET /api/v1/security/compliance/summary` (Aggregate compliance reporting metrics)
- `GET /api/v1/security/retention/policies` (List data retention policies)
- `POST /api/v1/security/retention/policies` (Create/update retention policy)
- `GET /api/v1/security/holds` (List active and released legal/clinical holds)
- `POST /api/v1/security/holds` (Place new legal/clinical hold)
- `POST /api/v1/security/holds/{hold_id}/release` (Release existing hold)

### FHIR R4 Endpoints (`backend/app/api/v1/endpoints/fhir.py`)
- `GET /api/v1/fhir/Consent/{consent_id}` (`FHIRConsent` resource)
- `GET /api/v1/fhir/AuditEvent/{event_id}` (`FHIRAuditEvent` resource)
- `GET /api/v1/fhir/Provenance/security/{event_id}` (`FHIRProvenance` resource)
- `GET /api/v1/fhir/patients/{patient_id}/consents` (`FHIRBundle` of Consent resources)

---

## 5. Background Asynchronous Workers (`task_service.py`)
- `AUDIT_LOG_INTEGRITY_CHECK`: Scans audit log hash chain for verification.
- `SECURITY_ANOMALY_SCAN`: Batch evaluates recent access logs for anomalous behavior.
- `DATA_RETENTION_EVALUATION`: Evaluates records against retention policies and active holds.
- `COMPLIANCE_REPORT_GENERATION`: Asynchronously synthesizes deep compliance audit reports.

---

## 6. Frontend Workspace (`SecurityComplianceWorkspace.tsx`)
Interactive security console in `frontend/src/components/security/SecurityComplianceWorkspace.tsx`:
1. **Security Overview Dashboard**: Integrity verification banner, active holds badge, incident counts by severity, compliance health gauges.
2. **Immutable Audit Trail Explorer**: Searchable, filterable audit log viewer with SHA-256 hash badges and non-PHI metadata inspector.
3. **Patient Consent Directives**: Patient consent registry, new consent modal with digital signature hashing, immediate revocation controls.
4. **Security Incident Queue**: Incident severity filters (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), status transitions (`OPEN` -> `INVESTIGATING` -> `RESOLVED`), resolution notes editor.
5. **Data Retention & Legal Holds**: Policy table, legal hold placement modal, safety protections indicating hold enforcement.
6. **Compliance Reports & FHIR Resource Inspector**: On-demand compliance report generator with export capability, and interactive FHIR R4 `Consent` & `AuditEvent` JSON viewer.
7. **Dashboard Integration**: Registered as `🛡️ Security & Compliance` tab in `DashboardPage.tsx`.

---

## 7. Verification Strategy
1. **Backend Tests (`backend/tests/test_clinical_security_compliance.py`)**:
   - Audit event emission and non-PHI validation.
   - Tamper-evident SHA-256 hash-chain verification.
   - Patient consent grant, evaluation, and immediate revocation enforcement.
   - Cross-patient unauthorized access detection and security incident creation.
   - Incident resolution lifecycle.
   - Data retention policies and legal hold preservation safeguards.
   - FHIR R4 `Consent`, `AuditEvent`, and `Provenance` serialization and export.
   - Compliance summary generation.
2. **Frontend Tests (`frontend/src/test/security.test.tsx`)**:
   - Renders security overview, audit events, consent manager, incident queue, and legal holds.
   - Grants and revokes patient consent.
   - Resolves security incidents with notes.
   - Places and releases legal holds.
   - Displays FHIR R4 Consent and AuditEvent JSON representations.
3. **Full Regression & Verification**:
   - Pytest multi-suite backend regression.
   - Alembic migration SQL verification: `alembic upgrade head --sql`.
   - Frontend Vitest suite execution (all test suites).
   - Production bundle build: `npm run build`.

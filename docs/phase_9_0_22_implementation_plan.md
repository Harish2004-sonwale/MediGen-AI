# Phase 9.0.22 Revised Implementation Plan: Enterprise Reliability, Clinical Concurrency, Multi-Tenant Isolation, Interoperability, Security & AI Governance

**System Name**: MediGen AI — Enterprise Clinical Decision Support & Health Intelligence Platform
**Baseline Commit**: [`28ea30d`](https://github.com/Harish2004-sonwale/MediGen-AI/commit/28ea30d) (`feat: add enterprise EHR integration and real-time collaboration`)
**Branch**: `main` (Synchronized with `origin/main`)
**Evaluation Date**: 2026-08-31
**Source of Truth**: [`docs/phase_9_0_22_architecture_review.md`](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/docs/phase_9_0_22_architecture_review.md)
**Status**: DRAFT IMPLEMENTATION PLAN — READY FOR APPROVAL (No code or migrations executed)

---

## 1. Executive Summary & Purpose

Phase 9.0.21 established foundational interoperability and multi-tenancy models (SMART 2.0 PKCE, CDS Hooks 2.0, WebSockets/WebRTC signaling, terminology normalization, and health system tenant tables in Migration 0022).

Phase 9.0.22 addresses the **core architectural, reliability, concurrency, clinical safety, and security gaps** identified in the architecture review. Its objective is to prepare MediGen AI for multi-worker hospital cluster deployments by introducing:
1. **Transactional Outbox Pattern** with at-least-once task delivery guarantees and dead-letter queue (DLQ) replay.
2. **Redis-backed Clustered WebSocket Backplane** extending the existing `WebSocketManager` for multi-worker load balancing.
3. **Optimistic Concurrency & CPOE Idempotency Guards** preventing duplicate orders and race conditions during simultaneous care team chart modifications.
4. **Allergy Class Cross-Reactivity & Automated Alert Escalation** protecting against pharmacological class hypersensitivity (beta-lactams, sulfonamides, NSAIDs) and unattended critical telemetry alerts.
5. **Relationship-Driven Multi-Tenant Clinical Isolation (Migration 0023)** mapping `facility_id` foreign keys with validated backfill across clinical tables.
6. **Dynamic SMART Cryptographic RS256 Keystore & Token Revocation** supporting live asymmetric JWKS key rotation and RFC 7009 token revocation.
7. **FHIR R4 Topic Subscriptions & Bulk Data ($export)** enabling real-time push events and population-level NDJSON exports.
8. **Multi-Factor Authentication (TOTP RFC 6238) & Redis Session Blacklisting** integrated seamlessly into the existing authentication engine.
9. **Automated Offline AI Grounding & Drift Evaluation Benchmark Harness** measuring hallucination rates and citation accuracy deterministically in CI without paid external APIs.
10. **Frontend Enterprise Workspace & Context Enhancements** incorporating tenant switching, MFA enrollment, FHIR subscription/bulk export consoles, and idempotency feedback.

---

## 2. Existing Architecture Protection & Compatibility

Phase 9.0.22 **EXTENDS and BUILDS UPON** the verified baseline at commit `28ea30d`. It strictly avoids duplicating or replacing existing verified components:

| Existing Component | Current Repository Location | Phase 9.0.22 Enhancement Strategy |
|---|---|---|
| **Redis Caching & Circuit Breaker** | `backend/app/core/cache.py` | **EXTENDS**: Retains cache logic; adds tenant-scoped key prefixes (`org:fac:key`) and session blacklisting. |
| **Sliding-Window Rate Limiter** | `backend/app/core/rate_limiter.py` | **EXTENDS**: Reuses sliding-window limiter; adds MFA attempt throttling (5 attempts/min). |
| **Celery Worker Infrastructure** | `backend/app/worker.py`, `task_service.py` | **EXTENDS**: Reuses Celery app & fallback sync worker; adds Outbox Relay periodic task and DLQ replay. |
| **WebSocket Connection Manager** | `backend/app/core/websocket_manager.py` | **EXTENDS**: Reuses `WebSocketManager` connection pools; adds Redis Pub/Sub backplane for multi-worker broadcast. |
| **SMART on FHIR 2.0 Service** | `backend/app/services/smart_service.py` | **EXTENDS**: Reuses SMART discovery & PKCE verification; upgrades static keys to dynamic RS256 keystore & RFC 7009 revocation. |
| **CDS Hooks 2.0 Dispatcher** | `backend/app/services/cds_hooks_service.py` | **EXTENDS**: Reuses hook dispatching and card schemas; wires allergy class checks into `order-select` and `order-sign`. |
| **FHIR R4 Translation Layer** | `backend/app/services/fhir_mapper_service.py` | **EXTENDS**: Reuses all 14 resource mappers; adds Subscription & Bulk Data ($export) streaming exporters. |
| **Authentication & RBAC** | `backend/app/core/security.py`, `api/deps.py` | **EXTENDS**: Reuses JWT validation & UserRole RBAC; adds TOTP MFA challenge and token blacklist validation. |
| **Audit Streaming & Observability** | `backend/app/core/observability.py` | **EXTENDS**: Reuses PHISanitizingFilter and Prometheus metrics; adds outbox, idempotency, and concurrency counters. |
| **Offline AI Fallback Engine** | `backend/app/ai/llm.py`, `safety_providers.py` | **EXTENDS**: Preserves offline determinism; adds offline evaluation harness and drug class hierarchy. |

---

## 3. Detailed Subsystem Specifications

---

### Subsystem 1: Transactional Outbox Pattern & Reliable Async Task Dispatcher (P0)

#### 1. Objective
Eliminate the dual-write vulnerability where database commits succeed but background task dispatching fails (or vice versa). Guarantee at-least-once delivery of asynchronous clinical tasks (document indexing, imaging analysis, timeline synthesis, audit verification) with dead-letter queue (DLQ) inspection and replay.

#### 2. Delivery Guarantees & Clarifications
- **Delivery Guarantee**: Strictly **AT-LEAST-ONCE**.
- **Exactly-Once Delivery**: Exactly-once delivery is physically impossible in distributed systems and is **NOT** claimed. Downstream consumers in Celery and background services are designed to be strictly **idempotent**.
- **Outbox Relay Safety**: Outbox relay workers use `SELECT ... FOR UPDATE SKIP LOCKED` to prevent duplicate concurrent processing across workers. Events failing dispatch are retried with exponential backoff up to `max_attempts=5`. If all retries fail, the event transitions to `DEAD_LETTER` state without event loss.
- **Audited Replay**: Manual or automated replay of dead-letter events creates an immutable audit trail entry recording the replaying user, timestamp, and previous error state.

#### 3. Exact Files Likely to Change
- `backend/app/services/task_service.py`
- `backend/app/services/document_service.py`
- `backend/app/services/imaging_service.py`
- `backend/app/services/timeline_service.py`
- `backend/app/worker.py`

#### 4. New Files Required
- `backend/app/models/outbox.py`
- `backend/app/schemas/outbox.py`
- `backend/app/services/outbox_service.py`
- `backend/app/api/v1/endpoints/outbox.py`
- `backend/tests/test_outbox_and_dlq.py`

#### 5. Database Changes (Migration 0023)
- Create `outbox_events` table:
  - `id`: Integer primary key (auto-increment)
  - `event_id`: String(64), unique, indexed (format `EVT-YYYYMMDD-XXXX`)
  - `event_type`: String(64), indexed (`DOCUMENT_INDEXING`, `IMAGING_ANALYSIS`, `TIMELINE_SUMMARY`, `AUDIT_VERIFICATION`, `FHIR_SUBSCRIPTION_TRIGGER`)
  - `aggregate_type`: String(64) (`MedicalDocument`, `ImagingStudy`, `Patient`, `Encounter`)
  - `aggregate_id`: String(64)
  - `facility_id`: String(64), indexed, foreign key to `clinical_facilities(facility_id)`
  - `payload_json`: JSON, contains task parameters and execution metadata
  - `status`: String(32), indexed, default `'PENDING'` (`'PENDING'`, `'PUBLISHED'`, `'FAILED'`, `'DEAD_LETTER'`)
  - `attempts`: Integer, default 0
  - `max_attempts`: Integer, default 5
  - `last_error`: Text, nullable
  - `retry_after`: DateTime with timezone, nullable
  - `published_at`: DateTime with timezone, nullable
  - `created_at`: DateTime with timezone, default `now()`, indexed

#### 6. API Changes
- `GET /api/v1/tasks/outbox` — List pending, failed, or dead-letter outbox events (Admin/Auditor only).
- `POST /api/v1/tasks/outbox/{event_id}/replay` — Manually retry a dead-letter event.
- `GET /api/v1/tasks/outbox/stats` — Outbox queue backlog and failure rate metrics.

#### 7. Service-Layer Changes
- `outbox_service.py`:
  - `create_outbox_event(db: Session, event_type: str, aggregate_type: str, aggregate_id: str, payload: dict, facility_id: Optional[str]) -> OutboxEvent`: Inserts outbox event inside the active caller's SQLAlchemy transaction.
  - `relay_pending_outbox_events(db: Session, batch_size: int = 50) -> int`: Dispatches pending events to Celery/worker with exponential backoff on network errors.
  - `replay_dead_letter_event(db: Session, event_id: str, replaying_user_id: int) -> bool`: Resets status to `PENDING` and logs an administrative audit event.

#### 8. Background Worker Changes
- Celery periodic task `outbox_relay_worker` executing every 5 seconds.

#### 9. Frontend Changes
- Admin Compliance Workspace includes an Outbox Backlog & DLQ Replay Console.

#### 10. Security & Safety
- Payloads store entity IDs and operational metadata; raw clinical record text is not stored in outbox logs. Access restricted to `ADMIN` and `AUDITOR` roles.

#### 11. Priority
- **P0** (Critical Data Integrity & Reliability).

---

### Subsystem 2: Clustered Redis Pub/Sub WebSocket Backplane (P0)

#### 1. Objective
Enable horizontal multi-worker / multi-container scaling of real-time clinical WebSockets (ECG telemetry, clinician co-annotation, WebRTC signaling) across load-balanced processes via Redis Pub/Sub, extending the existing `WebSocketManager` without creating parallel architectures.

#### 2. Architecture & Channel Convention
- **Channel Naming Convention**:
  - Live Telemetry: `medigen:ws:telemetry:{facility_id}:{patient_id}`
  - Clinician Collaboration: `medigen:ws:collab:{facility_id}:{patient_id}`
  - Telehealth Signaling: `medigen:ws:telehealth:{facility_id}:{session_id}`
- **Authorization before Subscription**: Clinicians must present a valid JWT; `WebSocketManager` verifies that the clinician has read access to the target patient and facility before accepting the connection.
- **Rate Limiting & Backpressure**: Incoming client messages are capped at 50 msg/sec per socket using a token bucket. High-frequency ECG frames use a drop-oldest buffer strategy during network congestion to prevent memory ballooning.
- **Reconnect & Degradation**: Frontend implements exponential reconnect backoff ($1\text{s} \to 2\text{s} \to 4\text{s} \to \max 30\text{s}$). If Redis is unreachable, `WebSocketManager` degrades gracefully to local in-memory broadcasting and logs a high-priority warning without terminating active connections.

#### 3. Exact Files Likely to Change
- `backend/app/core/websocket_manager.py`
- `backend/app/api/v1/endpoints/websockets.py`
- `frontend/src/api/client.ts`

#### 4. New Files Required
- `backend/tests/test_websocket_redis_backplane.py`

#### 5. API & Service Changes
- `WebSocketManager`:
  - `start_redis_listener(redis_client)`: Async background task listening to `medigen:ws:*` channels and relaying frames to local WebSocket connections.
  - `broadcast_telemetry`, `broadcast_collaboration`, `forward_telehealth_signaling`: Publish to Redis when Redis is active, with local memory fallback.
  - Strict production JWT validation: In production (`settings.is_production() == True`), requests without valid JWT are rejected immediately with `WebSocketClose(code=1008)`.

#### 6. Priority
- **P0** (Clustered Real-Time Architecture).

---

### Subsystem 3: Optimistic Concurrency & CPOE Idempotency Guards (P0)

#### 1. Objective
Prevent lost updates during simultaneous care team record edits, and guarantee idempotency on mutating clinical API endpoints during network retries without blocking legitimate repeated clinical orders.

#### 2. Specific Models & Endpoints Requiring Versioning
- **Models Requiring Optimistic Concurrency**:
  - `Order` (`orders.version` INT default 1) — Concurrent physician order signing / modification.
  - `CarePlan` (`care_plans.version` INT default 1) — Multi-disciplinary care plan goal updates.
  - `DischargeProtocol` (`discharge_protocols.version` INT default 1) — Simultaneous nurse/physician discharge sign-offs.
- *(Read-only or immutable append-only tables like `vital_signs`, `audit_logs`, `chat_messages` do NOT require versioning).*

#### 3. Concurrency Conflict Handling
- When a stale version update is attempted, SQLAlchemy raises `StaleDataError`.
- API catches this and returns `HTTP 409 Conflict` with:
  ```json
  {
    "error": "CONCURRENCY_CONFLICT",
    "message": "The clinical record has been modified by another clinician. Please refresh to inspect the latest state before reapplying your change.",
    "entity_type": "Order",
    "entity_id": "ORD-20260831-001",
    "current_version": 3
  }
  ```
- An audit entry is logged recording the concurrent conflict attempt.

#### 4. Idempotency vs. Legitimate Repeat Clinical Orders
- **Mutating Endpoints Scoped**: `POST /api/v1/orders/`, `PUT /api/v1/orders/{id}`, `POST /api/v1/care-plans/`, `PUT /api/v1/care-plans/{id}`, `POST /api/v1/transitions/discharge/{id}/signoff`.
- **Three Distinct Scenarios**:
  1. **Network / Client Retry** (Identical request payload, identical `Idempotency-Key` within 24h TTL): Returns cached response with header `X-Cache-Lookup: IDEMPOTENT-HIT`. No duplicate order created.
  2. **Duplicate HTTP Request with New Key**: Executes CPOE creation; safety engine detects duplicate active drug therapy and issues a CDS advisory requiring explicit clinician override reason.
  3. **Intentionally Repeated Clinical Order**: Clinician sends a second order with a new `Idempotency-Key` and provides explicit duplicate therapy override rationale (e.g. "Increased dosage for acute flare-up" or "Subsequent bolus"). The order is created successfully without rejection.

#### 5. Exact Files Likely to Change
- `backend/app/models/order.py`
- `backend/app/models/care_plan.py`
- `backend/app/models/discharge.py`
- `backend/app/services/order_service.py`
- `backend/app/services/care_plan_service.py`
- `backend/app/api/v1/endpoints/orders.py`
- `backend/app/api/v1/endpoints/care_plans.py`

#### 6. New Files Required
- `backend/app/core/idempotency.py`
- `backend/app/models/idempotency.py`
- `backend/tests/test_concurrency_and_idempotency.py`

#### 7. Database Changes (Migration 0023)
- Add `version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)` to `orders`, `care_plans`, `discharge_protocols`.
- Create `idempotency_records` table:
  - `id`: Integer primary key
  - `idempotency_key`: String(128), unique, indexed
  - `endpoint`: String(128), indexed
  - `user_id`: Integer, indexed
  - `facility_id`: String(64), indexed
  - `request_hash`: String(64) (SHA-256 of normalized body)
  - `response_code`: Integer
  - `response_body`: Text
  - `created_at`: DateTime with timezone, default `now()`
  - `expires_at`: DateTime with timezone, indexed (TTL 24 hours)

#### 8. Priority
- **P0** (Clinical Safety & Concurrency).

---

### Subsystem 4: Allergy Class Cross-Reactivity & Critical Alert Escalation (P0)

#### 1. Objective
Enhance clinical decision support safety by detecting pharmacological class-level cross-sensitivities (beta-lactams, sulfonamides, NSAIDs) and providing automated fail-safe escalation timers for unacknowledged critical telemetry alerts.

#### 2. Clinical Decision Support Safety Disclaimer
> **Clinical Disclaimer**: Allergy cross-reactivity checks and alert escalation timers are automated decision-support aids designed to reduce adverse events and alert fatigue. They do not replace the professional clinical judgment of a licensed healthcare provider.

#### 3. Deterministic Drug Class Hierarchy
- **Beta-Lactams Class**:
  - Penicillins (amoxicillin, ampicillin, penicillin V/G, piperacillin)
  - Cephalosporins (cefazolin, cephalexin, ceftriaxone, cefepime)
  - Carbapenems (meropenem, imipenem)
  - *Cross-Reactivity Risk*: Exact substance match $\to$ `CRITICAL`; Penicillin $\leftrightarrow$ Cephalosporin $\to$ `HIGH` (3-5% cross-reactivity warning, requires clinician rationale); Penicillin $\leftrightarrow$ Carbapenem $\to$ `MODERATE`.
- **Sulfonamides Class**:
  - Sulfamethoxazole, sulfadiazine, sulfasalazine $\leftrightarrow$ Thiazide/Loop diuretics class warning.
- **NSAIDs Class**:
  - Ibuprofen, naproxen, ketorolac, meloxicam $\leftrightarrow$ Aspirin (Aspirin-Exacerbated Respiratory Disease warning).
- **Safe Fallback for Unmapped Terminology**: If a drug or allergy substance cannot be mapped to a known class, the engine generates a `MODERATE` advisory banner ("Unverified substance pharmacology; clinician review advised") rather than failing silently.

#### 4. Critical Alert Escalation Engine
- **Lifecycle States**: `CREATED` $\to$ `ACTIVE` $\to$ `ESCALATED_TEAM` (if unacknowledged after 15 min) $\to$ `ESCALATED_SUPERVISOR` (if unacknowledged after 30 min) $\to$ `ACKNOWLEDGED` $\to$ `RESOLVED`.
- **Race Condition Safety**: If two clinicians acknowledge an alert simultaneously, the first write transitions the alert to `ACKNOWLEDGED`; the second receives the updated state with the acknowledging clinician's name.
- **Fail-Safe Polling**: If Celery or Redis is temporarily down, alerts remain safely stored in PostgreSQL; when workers reconnect, the escalation scanner processes all overdue alerts without skipping.

#### 5. Exact Files Likely to Change
- `backend/app/ai/safety_providers.py`
- `backend/app/services/safety_service.py`
- `backend/app/services/vital_service.py`
- `backend/app/models/alert.py`
- `backend/app/schemas/safety.py`

#### 6. New Files Required
- `backend/app/ai/allergy_cross_reactivity_provider.py`
- `backend/tests/test_allergy_and_escalation.py`

#### 7. Database Changes (Migration 0023)
- Update `clinical_alerts` table:
  - Add `facility_id`: String(64), indexed
  - Add `escalation_level`: Integer, default 0 (`0=ACTIVE`, `1=ESCALATED_TEAM`, `2=ESCALATED_SUPERVISOR`)
  - Add `escalated_at`: DateTime with timezone, nullable
  - Add `escalation_notes`: Text, nullable

#### 8. Priority
- **P0** (Clinical Safety).

---

### Subsystem 5: Relationship-Driven Multi-Tenant Clinical Isolation (Migration 0023) (P0)

#### 1. Objective
Enforce strict row-level database foreign keys and query dependencies guaranteeing cross-facility isolation across all clinical tables, while maintaining a safe, relationship-driven migration backfill strategy and audited emergency break-glass overrides.

#### 2. Detailed Table-by-Table Relationship & Backfill Mapping

| Clinical Table | Current Ownership Relationship | Proposed Facility Foreign Key | Relationship-Driven Backfill Source |
|---|---|---|---|
| `users` | Global system user | `default_facility_id` $\to$ `clinical_facilities(facility_id)` | Default facility `FAC-001` or first facility in user's assigned organization. |
| `patients` | Global demographic record | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived from patient's primary encounter attending doctor's facility, or fallback seed `FAC-001` (`provenance='MIGRATION_BACKFILL'`). |
| `encounters` | Linked to `patient_id` & `doctor_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived from attending `Doctor.department` mapped facility, or parent patient facility. |
| `orders` | Linked to `patient_id`, `encounter_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Encounter.facility_id`. |
| `clinical_notes`| Linked to `patient_id`, `encounter_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Encounter.facility_id`. |
| `medical_documents`| Linked to `patient_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Patient.facility_id`. |
| `care_plans` | Linked to `patient_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Patient.facility_id`. |
| `imaging_studies` | Linked to `patient_id`, `encounter_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived from parent `Encounter.facility_id` or `Patient.facility_id`. |
| `diagnostic_media`| Linked to `patient_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Patient.facility_id`. |
| `clinical_alerts` | Linked to `patient_id` | `facility_id` $\to$ `clinical_facilities(facility_id)` [INDEXED] | Derived directly from parent `Patient.facility_id`. |

#### 3. Migration Safety & Multi-Phase Backfill Execution
1. **Phase 1: Seed Validation**: Ensure root organization `ORG-001` ('MetroHealth Network') and facility `FAC-001` ('MetroHealth General Hospital') exist.
2. **Phase 2: Nullable Column Addition**: Add `facility_id VARCHAR(64)` as **NULLABLE** across all 10 clinical tables.
3. **Phase 3: Relationship-Driven Backfill**: Execute SQL UPDATE statements resolving `facility_id` via parent `encounters` and `patients` relations; assign fallback `FAC-001` only where no parent relation exists.
4. **Phase 4: Validation Query**: Execute `SELECT count(*) WHERE facility_id IS NULL` across all 10 tables. If count > 0, abort migration with error.
5. **Phase 5: Constraint Enforcement**: Apply `ALTER TABLE ... ALTER COLUMN facility_id SET NOT NULL`, foreign key constraints, and B-tree indexes.

#### 4. Query-Level Tenant Enforcement & Break-Glass
- `TenantContext` dependency in `backend/app/core/tenant_context.py` evaluates `X-Facility-ID` header.
- Helper `apply_tenant_filter(query, ModelClass, tenant_ctx)` automatically injects `WHERE ModelClass.facility_id == tenant_ctx.facility_id`.
- If a clinician requires emergency access to a patient from another facility, they activate Break-Glass Consent (`is_break_glass=True`, with mandatory reason); access is granted and immediately logged to the immutable security audit log.

#### 5. Exact Files Likely to Change
- `backend/app/models/patient.py`
- `backend/app/models/encounter.py`
- `backend/app/models/order.py`
- `backend/app/models/note.py`
- `backend/app/models/document.py`
- `backend/app/models/care_plan.py`
- `backend/app/models/imaging.py`
- `backend/app/models/media.py`
- `backend/app/models/user.py`
- `backend/app/api/deps.py`
- `backend/app/services/tenant_service.py`

#### 6. New Files Required
- `backend/alembic/versions/0023_multi_tenant_clinical_isolation_and_outbox.py`
- `backend/app/core/tenant_context.py`
- `backend/tests/test_tenant_row_level_isolation.py`

#### 7. Priority
- **P0** (Core Multi-Tenancy & Data Isolation).

---

### Subsystem 6: Dynamic SMART RS256 Keystore & Token Revocation (P1)

#### 1. Objective
Upgrade SMART on FHIR 2.0 authentication from static mock RSA strings to dynamic cryptographic RS256 keypair generation with rotation in `jwks.json` and implement RFC 7009 token revocation, extending the existing `SmartService`.

#### 2. Architecture & Keystore Rotation
- **Dynamic RSA Keystore**: Generates 2048-bit RSA keypair on initialization with unique `kid` (e.g. `medigen-key-2026-08`). Formats public modulus `n` and exponent `e` to RFC 7517 JWK standard.
- **Rotation Window**: `jwks.json` publishes current active key and previous active key for 24 hours to ensure in-flight tokens validate seamlessly during key rotation.
- **RFC 7009 Token Revocation**: `POST /api/v1/smart/revoke` accepts `token` and `token_type_hint`. Revocation records the token hash in Redis (`SETEX medigen:revoked:token:{hash} {ttl} 1`).
- **Token Verification**: Token introspection and API authorization check the Redis revocation blacklist before accepting SMART access tokens.

#### 3. Exact Files Likely to Change
- `backend/app/services/smart_service.py`
- `backend/app/api/v1/endpoints/smart.py`
- `backend/app/schemas/smart.py`

#### 4. New Files Required
- `backend/app/core/smart_keystore.py`
- `backend/tests/test_smart_keystore_and_revocation.py`

#### 5. Priority
- **P1** (Enterprise SMART on FHIR Interoperability).

---

### Subsystem 7: FHIR R4 Topic Subscriptions & Bulk Data Export ($export) (P1)

#### 1. Objective
Implement FHIR R4 Subscription dispatching (Topic-based push via REST-hooks and WebSockets) and asynchronous Bulk Data ($export) generating NDJSON file streams for population health analytics.

#### 2. Clarification on Bulk Data Compliance
> **Testing Clarification**: Local unit and integration tests verify the protocol implementation, NDJSON generation, and status polling within MediGen AI. Formal Bulk Data compliance (e.g. ONC (g)(10) certification) requires end-to-end testing against external certified EHR gateways.

#### 3. Architecture & Asynchronous Export Flow
- **FHIR Subscriptions**:
  - Topics: `patient-admit`, `encounter-close`, `order-created`, `vital-critical`.
  - Delivery Channels: `rest-hook` (HTTP POST with HMAC secret token) and `websocket` (live frame).
- **Bulk Data ($export)**:
  - `GET /api/v1/fhir/Patient/$export` initiates async job and returns `HTTP 202 Accepted` with `Content-Location: /api/v1/fhir/bulk-export/status/{job_id}`.
  - Background Celery task streams patient records, conditions, observations, and medications to storage in NDJSON format (`Patient.ndjson`, `Observation.ndjson`).
  - Polling endpoint returns download URLs when `status == 'COMPLETED'`. Files auto-expire after 24 hours.

#### 4. Exact Files Likely to Change
- `backend/app/services/fhir_export_service.py`
- `backend/app/api/v1/endpoints/fhir.py`
- `backend/app/schemas/fhir.py`

#### 5. New Files Required
- `backend/app/models/fhir_subscription.py`
- `backend/app/models/bulk_export.py`
- `backend/app/services/fhir_subscription_service.py`
- `backend/app/services/bulk_export_service.py`
- `backend/tests/test_fhir_subscriptions_and_bulk.py`

#### 6. Database Changes (Migration 0023)
- Create `fhir_subscriptions` table (`subscription_id`, `facility_id`, `topic`, `criteria`, `channel_type`, `endpoint_url`, `secret_token`, `status`, `created_at`).
- Create `bulk_export_jobs` table (`job_id`, `facility_id`, `user_id`, `export_type`, `status`, `output_urls_json`, `expires_at`, `created_at`).

#### 7. Priority
- **P1** (Enterprise Interoperability).

---

### Subsystem 8: Multi-Factor Authentication (TOTP) & Redis Session Blacklisting (P1)

#### 1. Objective
Implement standard Time-based One-Time Password (TOTP RFC 6238) two-factor authentication and Redis-backed session token revocation, integrated directly into the existing authentication and security architecture.

#### 2. Architecture & Security Flow
- **TOTP RFC 6238 Protocol**: Pure Python HMAC-SHA1 6-digit code computation with 30-second time steps ($\pm 1$ window tolerance).
- **Secret Protection**: TOTP secrets are encrypted at rest using AES-256 before storage in `mfa_credentials`.
- **Backup Recovery Codes**: Generates 8 single-use recovery codes stored as SHA-256 hashes.
- **Login Challenge**: If user has MFA enabled, initial login returns `HTTP 200` with `mfa_required: true` and temporary 5-minute pre-auth token. Calling `POST /api/v1/auth/mfa/validate` with valid TOTP code issues full clinical access token.
- **Throttling & Brute-Force Defense**: MFA validation attempts are rate-limited to 5 attempts/min per user via `RateLimiter`.
- **Instant Logout Blacklisting**: `POST /api/v1/auth/logout` records the active JWT JTI/hash in Redis blacklist (`SETEX medigen:blacklist:token:{hash} {remaining_ttl} 1`).

#### 3. Exact Files Likely to Change
- `backend/app/core/security.py`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/deps.py`
- `backend/app/schemas/user.py`

#### 4. New Files Required
- `backend/app/models/mfa.py`
- `backend/app/services/mfa_service.py`
- `backend/tests/test_mfa_and_session_blacklisting.py`

#### 5. Database Changes (Migration 0023)
- Create `mfa_credentials` table (`id`, `user_id` UNIQUE FK, `secret_encrypted`, `is_enabled`, `backup_codes_json`, `last_used_at`, `created_at`).

#### 6. Priority
- **P1** (Enterprise IAM & Security Governance).

---

### Subsystem 9: Automated Offline AI Grounding & Drift Evaluation Harness (P1)

#### 1. Objective
Establish an automated, offline clinical AI evaluation harness that quantifies grounding precision, citation accuracy, hallucination resistance, and prompt injection defense against curated benchmark datasets deterministically in CI without external paid APIs.

#### 2. Safety & Certification Clarification
> **Governance Clarification**: Passing the automated evaluation harness verifies that clinical RAG models satisfy quantitative accuracy, citation precision, and prompt injection defense thresholds within the curated benchmark. It does not constitute legal or regulatory clinical device certification.

#### 3. Benchmark Dataset & Evaluation Metrics
- **Dataset Format (`backend/tests/data/clinical_eval_benchmark.json`)**: 20+ curated clinical scenarios covering multi-organ diagnoses, conflicting lab findings, medication reconciliation, missing data queries, and adversarial prompt injection attempts.
- **Quantitative Quality Thresholds**:
  - **Groundedness Score**: $\ge 95\%$ (Every fact statement must map to verified document chunk).
  - **Citation Precision**: $\ge 95\%$ (Cited chunk IDs must match source documents).
  - **Hallucination Rate**: **0%** (Zero fabricated entities or unsupported medical claims).
  - **Insufficient Information Accuracy**: **100%** (Must return standard fallback when data is missing).
  - **Adversarial Resilience**: **100%** (Prompt injections treated strictly as inert text data).
- **Execution Speed**: Completes deterministically in $<5$ seconds in CI using the offline clinical mock provider.

#### 4. Exact Files Likely to Change
- `backend/app/ai/llm.py`

#### 5. New Files Required
- `backend/app/ai/eval_harness.py`
- `backend/app/schemas/eval.py`
- `backend/tests/test_ai_evaluation_harness.py`
- `backend/tests/data/clinical_eval_benchmark.json`

#### 6. Priority
- **P1** (AI Safety & Governance).

---

### Subsystem 10: Frontend Enterprise Workspaces & Controls (P0/P1)

#### 1. Objective
Enhance frontend clinical user experience with multi-tenant facility switching, MFA security enrollment, FHIR Subscription/Bulk Export controls, and CPOE idempotency/concurrency conflict resolution modals.

#### 2. Exact Files Likely to Change
- `frontend/src/api/client.ts`
- `frontend/src/types/index.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/interop/SmartFhirEhrWorkspace.tsx`
- `frontend/src/components/tenants/HealthSystemTenantWorkspace.tsx`

#### 3. New Files Required
- `frontend/src/components/security/MfaEnrollmentModal.tsx`
- `frontend/src/components/interop/FhirSubscriptionsConsole.tsx`
- `frontend/src/components/orders/ConcurrencyConflictModal.tsx`
- `frontend/src/test/mfa.test.tsx`
- `frontend/src/test/outbox.test.tsx`

#### 4. Client API & UI Features
- `client.ts`: Adds `outboxApi`, `mfaApi`, `fhirSubscriptionApi`, `bulkExportApi`, and automatic `Idempotency-Key` / `X-Facility-ID` headers.
- Header: Facility Switcher dropdown with active facility badge.
- Order Entry: CPOE concurrency conflict modal and duplicate order warning.
- Security Settings: MFA QR enrollment and backup code download.

#### 5. Priority
- **P0/P1** (Frontend Enterprise UI).

---

## 4. Database Migration Plan: Migration 0023

### Migration Identifier
`0023_multi_tenant_clinical_isolation_and_outbox.py`

### Scope & Structure

```
+---------------------------------------------------------------------------------------------------+
|                                      MIGRATION 0023 EXECUTION PLAN                                 |
+---------------------------------------------------------------------------------------------------+
| STEP 1: Verify Seed Health System & Facility                                                      |
|   - Ensure health_organizations('ORG-001', 'MetroHealth Network') exists.                         |
|   - Ensure clinical_facilities('FAC-001', 'ORG-001', 'MetroHealth General Hospital') exists.      |
|                                                                                                   |
| STEP 2: Add Nullable Columns to Existing Clinical Tables                                          |
|   - users:              + default_facility_id VARCHAR(64)                                         |
|   - patients:           + facility_id VARCHAR(64)                                                 |
|   - encounters:         + facility_id VARCHAR(64)                                                 |
|   - orders:             + facility_id VARCHAR(64), + version INT DEFAULT 1                        |
|   - clinical_notes:     + facility_id VARCHAR(64)                                                 |
|   - medical_documents:  + facility_id VARCHAR(64)                                                 |
|   - care_plans:         + facility_id VARCHAR(64), + version INT DEFAULT 1                        |
|   - discharge_protocols:+ version INT DEFAULT 1                                                   |
|   - imaging_studies:    + facility_id VARCHAR(64)                                                 |
|   - diagnostic_media:   + facility_id VARCHAR(64)                                                 |
|   - clinical_alerts:    + facility_id VARCHAR(64), + escalation_level INT DEFAULT 0,              |
|                         + escalated_at TIMESTAMPTZ, + escalation_notes TEXT                       |
|                                                                                                   |
| STEP 3: Relationship-Driven Data Backfill                                                          |
|   - Backfill encounters from Doctor.department mapped facility.                                   |
|   - Backfill orders, notes, imaging from parent encounters.                                       |
|   - Backfill patients from primary encounter, or fallback 'FAC-001'.                             |
|   - Backfill remaining documents, care_plans, media, alerts from parent patients.                 |
|                                                                                                   |
| STEP 4: Validation Query & Constraint Enforcement                                                 |
|   - Assert 0 rows with facility_id IS NULL across all clinical tables.                            |
|   - ALTER TABLE ... ALTER COLUMN facility_id SET NOT NULL.                                        |
|   - Add foreign keys REFERENCES clinical_facilities(facility_id).                                 |
|   - Create B-tree indexes on facility_id columns.                                                 |
|                                                                                                   |
| STEP 5: Create New Core Reliability & Security Tables                                             |
|   - outbox_events:       id, event_id (UNIQUE), event_type, aggregate_type, aggregate_id,          |
|                         facility_id (FK), payload_json, status, attempts, max_attempts,           |
|                         last_error, retry_after, published_at, created_at                         |
|   - idempotency_records: id, idempotency_key (UNIQUE), endpoint, user_id, facility_id,             |
|                         request_hash, response_code, response_body, created_at, expires_at        |
|   - mfa_credentials:     id, user_id (UNIQUE FK), secret_encrypted, is_enabled,                   |
|                         backup_codes_json, last_used_at, created_at                               |
|   - fhir_subscriptions:  id, subscription_id (UNIQUE), facility_id, topic, criteria,              |
|                         channel_type, endpoint_url, secret_token, status, created_at              |
|   - bulk_export_jobs:    id, job_id (UNIQUE), facility_id, user_id (FK), export_type,             |
|                         status, output_urls_json, expires_at, created_at                          |
+---------------------------------------------------------------------------------------------------+
```

### Downgrade Strategy
- Reversible `downgrade()` function cleanly drops created tables and removes added columns without corrupting historical records.

---

## 5. Testing & Quality Assurance Strategy

### Backend Test Suites (`backend/tests/`)

| Test File | Focus Area | Verification Criteria |
|---|---|---|
| `test_outbox_and_dlq.py` | Transactional Outbox, Relay Worker, DLQ Replay | At-least-once delivery, exponential backoff, DLQ state, manual replay. |
| `test_websocket_redis_backplane.py` | Clustered WebSocketManager, Redis Pub/Sub | Cross-worker broadcast, WebRTC signaling, strict auth rejection. |
| `test_concurrency_and_idempotency.py` | Optimistic Locking, `Idempotency-Key` | `HTTP 409 Conflict`, idempotency hit vs. legitimate repeat order. |
| `test_allergy_and_escalation.py` | Beta-lactam/sulfa cross-reactivity, Alert Escalation | Class cross-reactivity warning, 15-min alert escalation timer. |
| `test_tenant_row_level_isolation.py` | Multi-Tenant Row Isolation, Break-Glass | Cross-facility access rejection, emergency break-glass audit log. |
| `test_smart_keystore_and_revocation.py` | RS256 JWKS Keystore, Token Revocation | Live RSA signature verification, RFC 7009 token revocation. |
| `test_fhir_subscriptions_and_bulk.py` | FHIR Subscriptions, Bulk $export | REST-hook dispatch, asynchronous NDJSON export generation. |
| `test_mfa_and_session_blacklisting.py` | TOTP MFA Challenge, Session Revocation | QR setup, 6-digit verification, backup codes, token blacklist. |
| `test_ai_evaluation_harness.py` | Offline Clinical RAG Benchmark | Groundedness $\ge 95\%$, citation $\ge 95\%$, hallucination $0\%$, injection $100\%$. |

### Frontend Test Suites (`frontend/src/test/`)

| Test File | Focus Area | Verification Criteria |
|---|---|---|
| `mfa.test.tsx` | MFA Enrollment & 2FA Challenge | QR modal rendering, 6-digit submission, backup code view. |
| `outbox.test.tsx` | Outbox Backlog & DLQ Replay | DLQ list rendering, manual replay trigger. |
| `subscriptions.test.tsx`| FHIR Subscriptions Console & Bulk Export | Subscription creation, $export job trigger & status poll. |
| `tenants.test.tsx` (ext)| Facility Switcher & Context Header | Facility dropdown switching, tenant context header update. |

---

## 6. Execution Order & Dependency Sequence

```
Step 1: Database Migration 0023
  └── Seed validation, backfill execution, constraint enforcement, new tables.

Step 2: Core Reliability & Concurrency (P0)
  ├── Implement outbox_service.py & Celery outbox relay worker.
  ├── Implement idempotency.py & optimistic locking on Order/CarePlan.
  ├── Implement tenant_context.py & query-level facility filters.
  └── Implement Redis Pub/Sub clustered WebSocketManager.

Step 3: Clinical Safety & Escalation (P0)
  ├── Implement allergy_cross_reactivity_provider.py (beta-lactam/sulfa/NSAID classes).
  └── Implement vital alert escalation background scanner.

Step 4: Enterprise Security & Interoperability (P1)
  ├── Implement smart_keystore.py (Dynamic RS256 JWKS & RFC 7009 token revocation).
  ├── Implement mfa_service.py (TOTP RFC 6238 & Redis session blacklisting).
  └── Implement fhir_subscription_service.py & bulk_export_service.py ($export NDJSON).

Step 5: AI Safety & Governance (P1)
  └── Implement eval_harness.py & clinical_eval_benchmark.json.

Step 6: Frontend Enterprise Workspaces
  ├── Update client.ts & types/index.ts.
  ├── Create MfaEnrollmentModal.tsx, FhirSubscriptionsConsole.tsx, ConcurrencyConflictModal.tsx.
  └── Update DashboardPage.tsx & Interop/Tenant workspaces.

Step 7: Full Automated Regression Verification
  ├── flake8 & bandit security scans.
  ├── pytest tests -q (Target: $\ge 475$ passed, 0 failed).
  ├── npx vitest run (Target: $\ge 75$ passed, 0 failed).
  ├── npm run build (tsc && vite build).
  └── alembic upgrade head --sql validation.
```

---

## 7. Verification Matrix

| Subsystem | Local Tests (Offline) | CI (GitHub Actions) | Staging Environment | External Hospital EHR | Production |
|---|---|---|---|---|---|
| **Transactional Outbox & DLQ** | ✅ In-memory SQLite / Celery sync | ✅ Automated pytest | Multi-container Celery/Postgres | N/A | Operational monitoring |
| **Clustered WebSockets** | ✅ Mock Pub/Sub loop | ✅ Automated pytest | Live Redis cluster | N/A | Clustered load balancer |
| **Optimistic Concurrency & Idempotency** | ✅ Parallel thread simulation | ✅ Automated pytest | Multi-client API stress test | EHR CPOE gateway | Hospital production |
| **Allergy Class Cross-Reactivity** | ✅ Deterministic rule table | ✅ Automated pytest | Clinical test patient charts | External drug DB sync | Clinical CDS advisory |
| **Multi-Tenant Row Isolation** | ✅ Multi-facility mock DB | ✅ Automated pytest | Multi-tenant tenant test suite | Multi-facility network | Hospital compliance |
| **SMART Dynamic RS256 & Revoke** | ✅ Pure Python cryptography | ✅ Automated pytest | SMART Sandbox launcher | Epic/Cerner App Orchard | Production EHR launch |
| **FHIR Subscriptions & Bulk $export** | ✅ NDJSON generator test | ✅ Automated pytest | Asynchronous worker stress | External FHIR client | Population health export |
| **TOTP MFA & Session Blacklist** | ✅ HMAC-SHA1 unit tests | ✅ Automated pytest | Real Authenticator App test | Hospital SSO integration | Production IAM |
| **AI Grounding Benchmark** | ✅ Curated benchmark suite | ✅ Automated pytest | Synthetic clinical corpus | N/A | Continuous AI audit |

---

## 8. Phase Boundary: What Phase 9.0.22 Will NOT Do

To maintain strict architectural focus and prevent scope creep:
- ❌ Will **NOT** build another generic Redis cache or rate limiter.
- ❌ Will **NOT** rewrite existing 14 FHIR R4 resource mappings.
- ❌ Will **NOT** implement complex multi-region active-active database replication.
- ❌ Will **NOT** introduce paid external commercial AI cloud subscriptions.
- ❌ Will **NOT** perform speculative full-stack UI redesigns.
- ❌ Will **NOT** introduce unrelated microservices.

---

## 9. Phase 9.0.22 Deliverables & Success Criteria

### Numbered Deliverables
1. **Migration 0023**: Schema expansion adding tenant foreign keys, version columns, and tables for outbox events, idempotency records, MFA credentials, FHIR subscriptions, and bulk export jobs.
2. **Transactional Outbox Engine**: Atomic event creation, background relay worker, and DLQ replay API.
3. **Clustered WebSocket Backplane**: Redis Pub/Sub integration for horizontal multi-worker WebSocket scaling.
4. **Optimistic Concurrency & Idempotency**: Version conflict handling (`HTTP 409`) and `Idempotency-Key` request deduplication.
5. **Allergy Class Cross-Reactivity & Alert Escalation**: Beta-lactam/sulfa/NSAID class checks and overdue alert escalation timers.
6. **Multi-Tenant Clinical Query Guards**: Row-level facility isolation with emergency break-glass auditing.
7. **SMART RS256 Keystore & Token Revocation**: Dynamic JWKS key rotation and RFC 7009 revocation endpoint.
8. **FHIR Subscriptions & Bulk Data $export**: Topic-based event push and asynchronous NDJSON export.
9. **TOTP Multi-Factor Authentication**: RFC 6238 2FA setup/verification and Redis session blacklisting.
10. **Offline AI Grounding Evaluation Harness**: Automated accuracy, groundedness, and hallucination scoring in CI.
11. **Frontend Enterprise UI**: Tenant switcher, MFA modal, FHIR subscription console, and concurrency conflict feedback.
12. **Documentation**: Comprehensive architecture walkthrough and verification guide in `docs/phase_9_0_22.md`.

### Measurable Success Criteria
- **Backend Test Suite**: $\ge 475$ tests passing with 0 failures in pytest.
- **Frontend Test Suite**: $\ge 75$ tests passing with 0 failures in Vitest.
- **Production Build**: `npm run build` (`tsc && vite build`) executes with 0 errors.
- **Security & Quality**: Flake8 (0 errors), Bandit (0 high/medium issues), and `git diff --check` (0 whitespace errors).
- **Alembic Integrity**: `alembic upgrade head --sql` validates revisions 0001 through 0023 seamlessly.

---

## 10. Implementation Readiness

### **IMPLEMENTATION STATUS: READY FOR IMPLEMENTATION**

The revised implementation plan has incorporated all multi-tenant backfill safety controls, existing architecture extensions, idempotency distinctions, concurrency limits, outbox at-least-once delivery guarantees, clinical safety disclaimers, and offline benchmark specifications.

*Standing by for user approval to begin execution of Phase 9.0.22.*

# Phase 9.0.21: Enterprise EHR Integration, SMART on FHIR 2.0 App Launch, CDS Hooks Ecosystem & Real-Time Multi-Clinician Collaboration — Implementation Plan

## 1. Executive Summary & Context

MediGen-AI has completed **Phases 9.0.1 through 9.0.20** (Commit `474c413`), establishing a verified, containerized, horizontally scalable Clinical Decision Support and Health Intelligence System with 414 passing backend tests (100%), 61 passing frontend tests (100%), and 21 Alembic database revisions.

**Phase 9.0.21** transitions MediGen-AI into an **interoperable enterprise hospital ecosystem platform**. It delivers:
1. **SMART on FHIR 2.0 App Launch Framework & OAuth2/OIDC Context**: Standard discovery (`/.well-known/smart-configuration`, `/.well-known/jwks.json`), PKCE-protected authorization flow, EHR launch context injection (`launch/patient`, `patient/*.read`), and token introspection.
2. **CDS Hooks 2.0 Standard Services & Card Engine**: Standard discovery (`GET /cds-services`), clinical hook adapters (`patient-view`, `order-select`, `order-sign`, `appointment-book`), and standardized CDS Cards (`info`, `warning`, `critical`, with action suggestions and SMART App links).
3. **Real-Time Bi-Directional WebSockets & Collaboration Channels**: WebSocket Connection Manager with Redis Pub/Sub backend for high-frequency ECG/SpO2 waveform telemetry, live multi-clinician chart co-annotation/whiteboard, and WebRTC signaling for peer-to-peer telehealth sessions.
4. **Multi-Tenant Health System & Facility Partitioning**: Database migration `0022_multi_tenant_facilities_and_ehr_integrations.py` introducing `HealthOrganization`, `ClinicalFacility`, `DepartmentUnit`, and `EHRIntegrationConfig` with tenant-scoped query filtering.
5. **Clinical Terminology Normalization & Semantic Cross-Walk Engine**: Centralized mapping service normalizing disparate laboratory, diagnostic, and medication codes into standard LOINC, SNOMED CT, RxNorm, and ICD-10-CM with semantic confidence scoring.
6. **Frontend SMART EHR & Real-Time Collaboration Workspaces**: Interactive SMART App launcher, CDS Hooks test simulator, and live collaboration/telemetry canvas.

---

## 2. Verified Baseline at Commit `474c413`

```text
Branch: main (synced with origin/main)
Latest Commit: 474c413 - feat: add platform hardening, production deployment and enterprise scalability
Backend Tests: 414 passed, 2 skipped, 0 failed (100% pass rate in 497.74s)
Frontend Tests: 61 passed out of 61 across 18 test files (100% pass rate in 15.31s)
Frontend Build: Clean compilation in 1.87s, 0 errors
Alembic Revisions: 21 migrations (0001 through 0021) generating valid DDL
Container Stack: 6 production services (postgres, redis, api, worker, frontend, ingress)
```

---

## 3. Phase 9.0.21 Objectives

1. **Enterprise EHR Interoperability**: Enable seamless embedding of MediGen-AI inside Epic, Cerner/Oracle Health, and Athenahealth workflows via standard SMART on FHIR 2.0.0 and CDS Hooks 2.0.
2. **Real-Time Clinical Telemetry & Collaboration**: Provide sub-100ms real-time vital waveform streaming and multi-clinician chart co-annotation without polling.
3. **Organizational Multi-Tenancy**: Enforce strict data and policy boundaries across regional health networks, hospital facilities, and clinical departments.
4. **Semantic Terminology Normalization**: Normalize inbound unstructured and legacy codes into authoritative LOINC, SNOMED CT, and RxNorm terminologies with deterministic offline mappings.
5. **Zero Clinical & Security Regressions**: Maintain 100% pass rate across all 414 existing backend tests and 61 frontend tests.

---

## 4. Detailed Target Architecture

```
                                  [ Enterprise EHR (Epic / Cerner) / Clinician Browser ]
                                                            │
                                        ┌───────────────────┴───────────────────┐
                                        ▼                                       ▼
                       [ SMART on FHIR 2.0 / CDS Hooks ]              [ WebSockets / WebRTC ]
                                        │                                       │
                                        ▼                                       ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │                 Nginx Edge Ingress Reverse Proxy                  │
                      │  - WSS / HTTPS TLS 1.3 Termination & Security Headers             │
                      │  - Rate Limiting Zones (SMART Auth: 5/s, CDS Hooks: 50/s)         │
                      └─────────────────┬───────────────────────────────┬─────────────────┘
                                        │                               │
                      /api/v1/*, /.well-known/*, /cds-services          /ws/* (WebSocket Upgrades)
                                        │                               │
                                        ▼                               ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │                    FastAPI ASGI Application                       │
                      │  ┌─────────────────────────┐  ┌────────────────────────────────┐  │
                      │  │ SMART on FHIR 2.0 Engine│  │ WebSocket Connection Manager   │  │
                      │  │ - PKCE & OAuth2 Server  │  │ - Redis Pub/Sub Multiplexing   │  │
                      │  │ - JWKS & Smart Config   │  │ - Telemetry Waveform Broadcaster│ │
                      │  │ - Token Introspection   │  │ - WebRTC Signaling Dispatcher  │  │
                      │  └──────────┬──────────────┘  └───────────────┬────────────────┘  │
                      │             │                                 │                   │
                      │  ┌──────────▼──────────────┐  ┌───────────────▼────────────────┐  │
                      │  │ CDS Hooks 2.0 Card Engine│ │ Terminology Normalization Engine│  │
                      │  │ - patient-view / order-*│  │ - LOINC, SNOMED CT, RxNorm     │  │
                      │  │ - Action Suggestions    │  │ - Semantic Distance Matcher    │  │
                      │  └──────────┬──────────────┘  └───────────────┬────────────────┘  │
                      │             │                                 │                   │
                      │  ┌──────────▼─────────────────────────────────▼────────────────┐  │
                      │  │ Multi-Tenant Facility Scoping & Cross-Facility Consent Guard│  │
                      │  └──────────────────────────┬──────────────────────────────────┘  │
                      └─────────────────────────────┼─────────────────────────────────────┘
                                                    │
                             ┌──────────────────────┴──────────────────────┐
                             ▼                                             ▼
              ┌─────────────────────────────┐               ┌─────────────────────────────┐
              │ PostgreSQL 16 Cluster       │               │ Redis 7 In-Memory Broker    │
              │ - Migration 0022 (Tenants)  │               │ - Telemetry Pub/Sub Channels│
              │ - Organizations & Facilities│               │ - SMART Authorization Codes │
              │ - EHR Integration Configs   │               │ - Rate Limit Counters       │
              │ - SHA-256 Audit Hash Chain  │               │ - Terminology Concept Cache │
              └─────────────────────────────┘               └─────────────────────────────┘
```

---

## 5. SMART on FHIR 2.0 Architecture & OAuth2/OIDC Flow

### 5.1 Standards Conformance
- Conforms to **HL7 SMART App Launch Implementation Guide (v2.0.0)**.
- Integrates with the existing [backend/app/api/v1/endpoints/fhir.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/api/v1/endpoints/fhir.py) and [backend/app/core/config.py](file:///c:/Users/HARISH%20SONWALE/Desktop/MediGen-AI/backend/app/core/config.py).

### 5.2 Discovery Endpoints
1. `GET /.well-known/smart-configuration`:
   - Returns standard JSON capabilities:
     ```json
     {
       "authorization_endpoint": "https://api.medigen.ai/api/v1/smart/authorize",
       "token_endpoint": "https://api.medigen.ai/api/v1/smart/token",
       "introspection_endpoint": "https://api.medigen.ai/api/v1/smart/introspect",
       "jwks_uri": "https://api.medigen.ai/api/v1/smart/jwks.json",
       "grant_types_supported": ["authorization_code", "client_credentials"],
       "code_challenge_methods_supported": ["S256"],
       "scopes_supported": [
         "openid", "profile", "fhirUser", "launch", "launch/patient", "launch/encounter",
         "patient/*.read", "patient/*.write", "user/*.read", "system/*.read"
       ],
       "response_types_supported": ["code"],
       "capabilities": [
         "launch-ehr", "launch-standalone", "client-public", "client-confidential-symmetric",
         "context-ehr-patient", "context-ehr-encounter", "permission-patient", "permission-user"
       ]
     }
     ```
2. `GET /.well-known/jwks.json` & `GET /api/v1/smart/jwks.json`:
   - Returns public RSA/EC key set for validating JWT tokens issued to SMART client apps.
   - Includes key rotation design (`kid` identifier, `use="sig"`, `alg="RS256"`).

### 5.3 PKCE & Launch Context Flow
1. **EHR Launch**: EHR embeds MediGen App iframe or redirects with `launch=<launch_id>` and `iss=<fhir_base_url>`.
2. **Authorization Request**: Client sends `GET /api/v1/smart/authorize` with `response_type=code`, `client_id`, `redirect_uri`, `scope`, `state`, `code_challenge`, `code_challenge_method=S256`, and `launch`.
3. **Consent & Verification**: System validates user session, tenant facility boundary, and scopes. Emits standard authorization code stored in Redis (TTL 300s).
4. **Token Exchange**: Client sends `POST /api/v1/smart/token` with `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, and `code_verifier`.
5. **Token Response**: Returns JWT `access_token`, `id_token` (OIDC), and launch context:
   ```json
   {
     "access_token": "<signed_jwt>",
     "token_type": "Bearer",
     "expires_in": 900,
     "scope": "launch/patient patient/Patient.read patient/Observation.read openid fhirUser",
     "id_token": "<signed_oidc_jwt>",
     "patient": "PAT-001",
     "encounter": "ENC-001",
     "facility_id": "FAC-001",
     "smart_style_url": "https://api.medigen.ai/api/v1/smart/style.json"
   }
   ```

---

## 6. CDS Hooks 2.0 Architecture & Card Ecosystem

### 6.1 Standards Conformance
- Conforms to **HL7 CDS Hooks Specification v2.0**.
- Acts as a standards-compliant adapter wrapping MediGen AI's existing clinical safety, RAG, vital alert, and CPOE order validation engines.

### 6.2 Discovery Endpoint: `GET /cds-services`
Registers active clinical decision-support services:
```json
{
  "services": [
    {
      "hook": "patient-view",
      "name": "medigen-patient-risk-advisor",
      "id": "medigen-patient-risk-advisor",
      "title": "MediGen Patient Risk & Care Gap Advisor",
      "description": "Evaluates patient clinical timeline, vital telemetry, and HEDIS care gaps on chart open.",
      "prefetch": {
        "patient": "Patient/{{context.patientId}}",
        "conditions": "Condition?patient={{context.patientId}}",
        "medications": "MedicationStatement?patient={{context.patientId}}"
      }
    },
    {
      "hook": "order-select",
      "name": "medigen-drug-safety-interceptor",
      "id": "medigen-drug-safety-interceptor",
      "title": "MediGen Drug-Drug & Contraindication Interceptor",
      "description": "Evaluates draft medication orders against active allergies, duplicate therapies, and drug interactions.",
      "prefetch": {
        "medications": "MedicationStatement?patient={{context.patientId}}",
        "allergies": "AllergyIntolerance?patient={{context.patientId}}"
      }
    },
    {
      "hook": "order-sign",
      "name": "medigen-critical-cpoe-verifier",
      "id": "medigen-critical-cpoe-verifier",
      "title": "MediGen Order Sign Safety & Precision Matcher",
      "description": "Validates final diagnostic and medication orders before signature."
    },
    {
      "hook": "appointment-book",
      "name": "medigen-appointment-optimizer",
      "id": "medigen-appointment-optimizer",
      "title": "MediGen Care Team & Conflict Optimizer",
      "description": "Validates clinician department schedule conflicts during appointment booking."
    }
  ]
}
```

### 6.3 CDS Card Schema & Advisory Rules
- **Indicators**: `info` (guidelines, tips), `warning` (moderate interaction, overdue screening), `critical` (severe contraindication, panic vital, duplicate therapy).
- **Suggestions**: Optional structured action drafts (`create`, `update`, `delete` FHIR resources).
- **Links**: SMART App launch links (`type="smart"`, `url="https://app.medigen.ai/smart/launch?patient=..."`).
- **Safety Policy**: CDS Cards are strictly **advisory**. MediGen AI never mutates clinical orders autonomously.

---

## 7. Real-Time WebSockets & Telemetry Streaming Architecture

### 7.1 WebSocket Connection Manager (`backend/app/core/websocket_manager.py`)
- Thread-safe connection registry with Redis Pub/Sub multiplexing across multi-node ASGI workers.
- **Authentication**: JWT token validation via `ws://.../ws/.../?token=<jwt_token>` during handshake.
- **Tenant & Patient Authorization**: Confirms user role and patient consent before subscribing.
- **Heartbeat & Liveness**: 30-second ping/pong frames; automatic client cleanup on disconnect.
- **Zero-PHI Logs**: Connection telemetry logs client IDs and channel names without clinical payload narratives.

### 7.2 Channel Inventory & Protocols
1. **`/ws/telemetry/{patient_id}`**:
   - High-frequency live vital telemetry streaming (ECG 12-lead waveforms at 250Hz decimation, SpO2 plethysmograph, and real-time alerts).
   - Rate limiting & backpressure: Decimated buffer flushed every 100ms.
2. **`/ws/collaboration/{patient_id}`**:
   - Multi-clinician real-time room presence (`user_joined`, `user_left`, `active_viewers`).
   - Shared cursor tracking and co-annotation on radiology findings and care plans.
3. **`/ws/telehealth/{session_id}`**:
   - WebRTC signaling server exchanging SDP offers, SDP answers, and ICE candidates between patient and clinician clients.
   - STUN/TURN configuration exported via `/api/v1/telehealth/ice-servers` (defaulting to standard public STUN servers for local deterministic testing).

---

## 8. Multi-Tenant Health System & Facility Partitioning

### 8.1 Data Model Architecture (`backend/app/models/tenant.py`)
- **`HealthOrganization`**: Top-level healthcare network (e.g., "Metropolitan Health System").
- **`ClinicalFacility`**: Individual hospital or outpatient clinic (e.g., "St. Jude Memorial Hospital", `facility_code="SJM-01"`).
- **`DepartmentUnit`**: Specialized ward or department (e.g., "Cardiology ICU", `dept_code="CICU-04"`).
- **`EHRIntegrationConfig`**: EHR vendor credentials and endpoints (Epic, Cerner, FHIR Base URL, Client ID, Secret, Signing Cert).

### 8.2 Tenant Scoping & Cross-Facility Consent
- Patient charts, encounters, and telemetry inherit `facility_id`.
- Clinicians operate within assigned facilities unless granted cross-facility emergency override privileges (`role="admin"` or `purpose_of_use="EMERGENCY"`).
- Cross-facility access triggers high-severity audit logging and verification against `patient_consents` policies.

---

## 9. Clinical Terminology Normalization & Semantic Cross-Walks

### 9.1 Terminology Engine Architecture (`backend/app/services/terminology_service.py`)
- Normalizes disparate laboratory, diagnostic, and medication descriptions into standard code systems:
  - **LOINC** (Logical Observation Identifiers Names and Codes): Standardizes lab tests and vitals (e.g., "Serum Potassium" $\rightarrow$ `6298-4`).
  - **SNOMED CT** (Systematized Nomenclature of Medicine): Standardizes clinical findings, conditions, and procedures (e.g., "Type 2 Diabetes" $\rightarrow$ `44054006`).
  - **RxNorm**: Standardizes medications and active ingredients (e.g., "Lisinopril 10 MG Oral Tablet" $\rightarrow$ `314076`).
  - **ICD-10-CM**: Standardizes billing and diagnostic classifications (e.g., "E11.9").
- **Deterministic Offline Concept Dictionary**: Built-in 2,000+ top clinical concept mapping database ensuring 100% offline testability.
- **Semantic Distance Scoring**: Calculates string similarity and Jaccard token overlap returning confidence scores (`0.0` to `1.0`) and match quality (`EXACT`, `HIGH_CONFIDENCE`, `SYNONYM_MATCH`, `UNMAPPED`).

---

## 10. Database Migration Design (Migration 0022)

**File**: `backend/alembic/versions/0022_multi_tenant_facilities_and_ehr_integrations.py`

### Tables to Create:
1. `health_organizations`:
   - `id` (PK, SERIAL), `org_id` (VARCHAR(64), UNIQUE, INDEX), `name` (VARCHAR(128)), `org_type` (VARCHAR(32)), `is_active` (BOOLEAN), `created_at`, `updated_at`.
2. `clinical_facilities`:
   - `id` (PK, SERIAL), `facility_id` (VARCHAR(64), UNIQUE, INDEX), `org_id` (FK $\rightarrow$ `health_organizations.org_id`), `name` (VARCHAR(128)), `facility_code` (VARCHAR(32), UNIQUE), `address_json` (JSON), `is_active` (BOOLEAN), `created_at`, `updated_at`.
3. `department_units`:
   - `id` (PK, SERIAL), `department_id` (VARCHAR(64), UNIQUE, INDEX), `facility_id` (FK $\rightarrow$ `clinical_facilities.facility_id`), `name` (VARCHAR(128)), `dept_code` (VARCHAR(32)), `floor_or_wing` (VARCHAR(64)), `is_active` (BOOLEAN), `created_at`, `updated_at`.
4. `ehr_integration_configs`:
   - `id` (PK, SERIAL), `config_id` (VARCHAR(64), UNIQUE, INDEX), `facility_id` (FK $\rightarrow$ `clinical_facilities.facility_id`), `ehr_vendor` (VARCHAR(32)), `fhir_base_url` (VARCHAR(255)), `client_id` (VARCHAR(128)), `smart_auth_url` (VARCHAR(255)), `smart_token_url` (VARCHAR(255)), `is_enabled` (BOOLEAN), `created_at`, `updated_at`.
5. `smart_auth_sessions`:
   - `id` (PK, SERIAL), `session_id` (VARCHAR(64), UNIQUE, INDEX), `client_id` (VARCHAR(128)), `user_id` (FK $\rightarrow$ `users.id`), `patient_id` (VARCHAR(64)), `encounter_id` (VARCHAR(64)), `facility_id` (VARCHAR(64)), `scope` (VARCHAR(500)), `code_challenge` (VARCHAR(128)), `code_challenge_method` (VARCHAR(16)), `auth_code` (VARCHAR(128), UNIQUE), `access_token_hash` (VARCHAR(64)), `expires_at` (TIMESTAMP), `created_at`.
6. `terminology_mappings`:
   - `id` (PK, SERIAL), `mapping_id` (VARCHAR(64), UNIQUE, INDEX), `source_system` (VARCHAR(64)), `source_code` (VARCHAR(64)), `source_display` (VARCHAR(255)), `target_system` (VARCHAR(64)), `target_code` (VARCHAR(64)), `target_display` (VARCHAR(255)), `confidence_score` (FLOAT), `is_verified` (BOOLEAN), `created_at`, `updated_at`.

---

## 11. API Endpoint Inventory

| Method | Endpoint Path | Auth / RBAC | Tenant Scope | Description | Audit Event |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/.well-known/smart-configuration` | Public | Global | SMART on FHIR 2.0 configuration manifest | None |
| `GET` | `/.well-known/jwks.json` | Public | Global | Public JSON Web Key Set for token validation | None |
| `GET` | `/api/v1/smart/authorize` | User Session | Facility | SMART OAuth2 Authorization endpoint with PKCE | `SMART_AUTH_REQUEST` |
| `POST` | `/api/v1/smart/token` | Basic / Public Client | Facility | SMART OAuth2 Token exchange endpoint | `SMART_TOKEN_ISSUED` |
| `POST` | `/api/v1/smart/introspect` | Confidential Client | Facility | Token introspection endpoint (RFC 7662) | `SMART_TOKEN_INTROSPECT` |
| `GET` | `/cds-services` | Public / Bearer | Global | CDS Hooks 2.0 Service Discovery | `CDS_DISCOVERY` |
| `POST` | `/cds-services/patient-view` | Bearer Token | Facility | CDS Hook for chart review & care gaps | `CDS_HOOK_PATIENT_VIEW` |
| `POST` | `/cds-services/order-select` | Bearer Token | Facility | CDS Hook for drug interactions & draft orders | `CDS_HOOK_ORDER_SELECT` |
| `POST` | `/cds-services/order-sign` | Bearer Token | Facility | CDS Hook for final signature safety check | `CDS_HOOK_ORDER_SIGN` |
| `POST` | `/cds-services/appointment-book` | Bearer Token | Facility | CDS Hook for department schedule validation | `CDS_HOOK_APPT_BOOK` |
| `GET` | `/api/v1/tenants/organizations` | Admin / Doctor | Tenant | List health organizations & facilities | `ORG_LIST` |
| `POST` | `/api/v1/tenants/facilities` | Admin | Tenant | Create or update clinical facility | `FACILITY_MUTATE` |
| `POST` | `/api/v1/terminology/normalize` | Doctor / Staff | Global | Normalize clinical concepts (LOINC, SNOMED, RxNorm) | `TERMINOLOGY_LOOKUP` |
| `GET` | `/api/v1/telehealth/ice-servers` | Authenticated | Global | Retrieve WebRTC STUN/TURN ice servers | `WEBRTC_ICE_REQUEST` |

---

## 12. WebSocket Endpoint Inventory

| Endpoint Path | Handshake Auth | Protocol / Channel | Payload Schema | Rate Limit / SLA |
| :--- | :--- | :--- | :--- | :--- |
| `WS /ws/telemetry/{patient_id}` | JWT query parameter | ECG & SpO2 live waveform buffer | `LiveTelemetryFrame` (decimated JSON/ArrayBuffer) | 10 frames/sec (100ms interval) |
| `WS /ws/collaboration/{patient_id}` | JWT query parameter | Presence, cursor, co-annotation | `CollaborationAction` (user, cursor_x, cursor_y, action) | Max 50 msgs/sec |
| `WS /ws/telehealth/{session_id}` | JWT query parameter | WebRTC SDP & ICE exchange | `WebRTCSignalingMessage` (offer, answer, candidate) | On-demand signaling |

---

## 13. Frontend Workspace Architecture

### New Workspace Components:
1. `frontend/src/components/interop/SmartFhirEhrWorkspace.tsx`:
   - Interactive SMART on FHIR App launcher (EHR launch simulator, standalone launch).
   - CDS Hooks 2.0 Live Playground: execute hooks (`patient-view`, `order-select`) and render standardized CDS Cards with action buttons.
   - EHR Integration management: configure vendor endpoints, view OAuth2 tokens, and inspect JWKS.
2. `frontend/src/components/collaboration/LiveCollaborationWorkspace.tsx`:
   - Real-time Multi-Clinician Collaboration Room: active clinician roster, shared cursor overlays.
   - 12-lead ECG & SpO2 canvas waveform visualizer rendering live WebSocket streams.
   - WebRTC Telehealth Video Room with audio/video toggle, screen share, and secure signaling.
3. `frontend/src/components/tenants/HealthSystemTenantWorkspace.tsx`:
   - Multi-tenant health system hierarchy tree (`Organization` $\rightarrow$ `Facility` $\rightarrow$ `Department`).
   - Facility-level clinical policy configuration and EHR connection status.

---

## 14. Testing & Verification Strategy

### 14.1 Backend Test Plan (`backend/tests/`)
1. `test_smart_on_fhir.py`:
   - Test `/.well-known/smart-configuration` and `/.well-known/jwks.json`.
   - Test PKCE authorization code generation and token exchange.
   - Test invalid `code_verifier`, expired auth code, and mismatched redirect URIs.
   - Test launch context injection (`patient`, `encounter`, `facility_id`).
2. `test_cds_hooks.py`:
   - Test `GET /cds-services` discovery.
   - Test `POST /cds-services/patient-view` returning risk and care gap CDS Cards.
   - Test `POST /cds-services/order-select` intercepting drug-drug interactions with warning cards and suggestion drafts.
   - Test `POST /cds-services/order-sign` and `POST /cds-services/appointment-book`.
3. `test_websockets_and_collaboration.py`:
   - Test WebSocket handshake authentication with valid/invalid JWTs.
   - Test `/ws/telemetry/{patient_id}` live waveform broadcasting.
   - Test `/ws/collaboration/{patient_id}` presence and cursor action exchange.
   - Test `/ws/telehealth/{session_id}` WebRTC SDP offer/answer exchange.
4. `test_multi_tenancy_and_facilities.py`:
   - Test tenant/facility creation and hierarchy.
   - Test cross-tenant data isolation (prevent Facility A users from viewing Facility B patients unless emergency override).
5. `test_terminology_normalization.py`:
   - Test LOINC lab normalization, SNOMED CT condition mapping, and RxNorm medication mapping with confidence scoring.

### 14.2 Frontend Test Plan (`frontend/src/test/`)
1. `smart.test.tsx`: Tests SMART launch simulation and CDS Hooks Card rendering.
2. `collaboration.test.tsx`: Tests real-time collaboration canvas, waveform visualizer, and WebRTC room status.
3. `tenants.test.tsx`: Tests health system organization tree and facility selector.

---

## 15. Implementation Sequence & Tasks

```
Task 1: Database Migration 0022 (Multi-Tenant & SMART Data Models)
Task 2: SMART on FHIR 2.0 Discovery & OAuth2/PKCE Core Backend
Task 3: CDS Hooks 2.0 Services & Standardized Card Formatter
Task 4: WebSocket Connection Manager & WebRTC Signaling Service
Task 5: Clinical Terminology Normalization Service
Task 6: Multi-Tenant Facility Scoping & Security Middleware
Task 7: Backend API & WebSocket Endpoint Routers
Task 8: Backend Unit & Integration Tests (100% Passing)
Task 9: Frontend SMART, Collaboration & Tenant Workspaces
Task 10: Frontend Vitest Tests & Production Build
Task 11: End-to-End Verification & Phase 9.0.21 Documentation
```

---

## 16. Component & Implementation Matrix

| Component | Planned | Offline Implementable | External Dependency | Risk | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SMART on FHIR 2.0 Core** | Complete OAuth2/PKCE & JWKS | ✅ Yes (Full offline mock/local) | Optional EHR vendor | Low | **P0 (Critical)** |
| **CDS Hooks 2.0 Services** | Standard discovery & 4 hook handlers | ✅ Yes (Full offline engine) | Optional EHR vendor | Low | **P0 (Critical)** |
| **WebSocket Waveform Hub** | Live ECG/SpO2 streaming | ✅ Yes (Local Redis Pub/Sub) | None | Medium | **P1 (High)** |
| **WebRTC Signaling** | SDP & ICE signaling exchange | ✅ Yes (Signaling layer only) | External STUN/TURN in prod | Medium | **P1 (High)** |
| **Multi-Tenant Facilities** | Org, Facility, Dept hierarchy | ✅ Yes (Alembic 0022) | None | Low | **P1 (High)** |
| **Terminology Normalizer** | LOINC/SNOMED/RxNorm mappings | ✅ Yes (Built-in dictionary) | None | Low | **P2 (Medium)** |
| **Frontend Workspaces** | SMART EHR & Collaboration UI | ✅ Yes (React 18 + Vitest) | None | Low | **P1 (High)** |

---

## 17. Readiness Declaration

- **Architecture**: READY
- **Implementation Plan**: COMPLETE
- **Code Implementation**: NOT STARTED
- **Git Commit**: NONE
- **Git Push**: NONE

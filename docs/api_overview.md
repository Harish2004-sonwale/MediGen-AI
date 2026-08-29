# MediGen-AI: REST API Reference & Overview

## 1. Authentication & User Management (`/api/v1/auth`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register new user (`patient`, `doctor`, `healthcare_staff`, `admin`) |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user and receive JWT access token |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve current user profile |

---

## 2. Patient Management (`/api/v1/patients`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/patients` | Admin / Staff | Create a new patient profile |
| `GET` | `/api/v1/patients` | Doctor / Staff / Admin | List and filter patients |
| `GET` | `/api/v1/patients/{patient_id}` | Authorized | Retrieve patient details |
| `PUT` | `/api/v1/patients/{patient_id}` | Admin / Staff | Update patient demographics |
| `DELETE` | `/api/v1/patients/{patient_id}` | Admin | Deactivate a patient record |

---

## 3. Doctor Management (`/api/v1/doctors`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/doctors` | Admin / Staff | Create a doctor profile |
| `GET` | `/api/v1/doctors` | Authenticated | List doctors with department/specialization filter |
| `GET` | `/api/v1/doctors/{doctor_id}` | Authenticated | Get doctor public details |
| `PUT` | `/api/v1/doctors/{doctor_id}` | Doctor (Self) / Admin | Update doctor profile details |
| `POST` | `/api/v1/doctors/{doctor_id}/verify` | Admin | Verify doctor medical license |
| `POST` | `/api/v1/doctors/{doctor_id}/reject` | Admin | Reject doctor verification |

---

## 4. Appointments & Encounters
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/appointments` | Authorized | Schedule a new appointment |
| `GET` | `/api/v1/appointments` | Authorized | List filtered appointments |
| `POST` | `/api/v1/appointments/{appointment_id}/confirm` | Doctor / Staff / Admin | Confirm scheduled appointment |
| `POST` | `/api/v1/appointments/{appointment_id}/cancel` | Authorized | Cancel appointment |
| `POST` | `/api/v1/encounters` | Doctor / Staff / Admin | Record a clinical encounter |
| `GET` | `/api/v1/encounters` | Authorized | List clinical encounters |

---

## 5. Medical Documents (`/api/v1/documents`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/documents/upload` | Authorized | Upload & index PDF, DOCX, or TXT document |
| `GET` | `/api/v1/documents` | Authorized | List authorized medical documents |
| `GET` | `/api/v1/documents/{document_id}` | Authorized | Retrieve document metadata |
| `GET` | `/api/v1/documents/{document_id}/chunks` | Authorized | Retrieve paginated text chunks |
| `DELETE` | `/api/v1/documents/{document_id}` | Admin / Uploader | Delete document, chunks, and ChromaDB vectors |

---

## 6. Clinical RAG (`/api/v1/rag`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/rag/query` | Authorized | Query patient records with grounded synthesis & citations |

---

## 7. Clinical Consultation Chat (`/api/v1/chat`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/chat/sessions` | Authorized | Create a patient-scoped consultation chat session |
| `GET` | `/api/v1/chat/sessions` | Authorized | List consultation sessions for a patient |
| `GET` | `/api/v1/chat/sessions/{session_id}` | Authorized | Get session detail and full turn history |
| `POST` | `/api/v1/chat/sessions/{session_id}/messages` | Authorized | Post message inquiry & receive grounded RAG answer |
| `POST` | `/api/v1/chat/sessions/{session_id}/messages/stream` | Authorized | Stream grounded consultation response via SSE (`text/event-stream`) |
| `DELETE` | `/api/v1/chat/sessions/{session_id}` | Authorized | Close and archive a consultation session |

### Longitudinal Clinical Intelligence & Safety
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}/timeline` | Authorized | Retrieve paginated chronological clinical timeline |
| `GET` | `/api/v1/patients/{patient_id}/timeline/summary` | Authorized | Generate RAG-grounded longitudinal narrative history summary |
| `POST` | `/api/v1/patients/{patient_id}/safety/check` | Authorized | Run clinical decision support safety evaluation (DDI, allergies, duplicates, contraindications) |

---

## 8. FHIR R4 Interoperability (`/api/v1/fhir`)
| Method | Path | Access | Description |
|---|---|---|---|
| `GET` | `/api/v1/fhir/Patient/{patient_id}` | Authorized | Export patient demographics as FHIR R4 `Patient` |
| `GET` | `/api/v1/fhir/Encounter/{encounter_id}` | Authorized | Export clinical encounter as FHIR R4 `Encounter` |
| `GET` | `/api/v1/fhir/Condition/{condition_id}` | Authorized | Export diagnosis as FHIR R4 `Condition` |
| `GET` | `/api/v1/fhir/MedicationStatement/{medication_id}` | Authorized | Export medication regimen as FHIR R4 `MedicationStatement` |
| `GET` | `/api/v1/fhir/Observation/{observation_id}` | Authorized | Export lab findings as FHIR R4 `Observation` |
| `GET` | `/api/v1/fhir/patients/{patient_id}/bundle` | Authorized | Export longitudinal history as a FHIR R4 `collection` `Bundle` |
| `POST` | `/api/v1/fhir/import` | Authorized / Staff | Ingest & persist a single FHIR R4 resource |
| `POST` | `/api/v1/fhir/Bundle` | Authorized / Staff | Batch import multiple resources from a FHIR R4 `Bundle` |

---

## 9. Background Asynchronous Tasks (`/api/v1/tasks`)
| Method | Path | Access | Description |
|---|---|---|---|
| `POST` | `/api/v1/tasks/documents/{document_id}/process` | Doctors / Staff / Admin | Enqueue background document extraction & vector indexing |
| `POST` | `/api/v1/tasks/timeline/{patient_id}/summary` | Doctors / Staff / Admin | Enqueue background longitudinal timeline summary compilation |
| `GET` | `/api/v1/tasks/{task_id}` | Authorized | Retrieve background task status, progress, and results |
| `GET` | `/api/v1/tasks` | Authorized | List authorized background tasks with filtering & pagination |
| `POST` | `/api/v1/tasks/{task_id}/retry` | Doctors / Staff / Admin | Re-enqueue a failed or cancelled background task |
| `POST` | `/api/v1/tasks/{task_id}/cancel` | Doctors / Staff / Admin | Cancel a pending background task |

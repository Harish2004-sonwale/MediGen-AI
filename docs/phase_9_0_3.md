# Phase 9.0.3 — Background Asynchronous Worker Architecture

## 1. Purpose

Phase 9.0.3 introduces a robust, extensible **Background Asynchronous Worker Architecture** for MediGen AI.

Clinical workflows often involve computationally intensive operations such as:
- Medical document text extraction (PDF, DOCX, TXT)
- Semantic chunking with clinical boundary preservation
- Embedding generation across clinical text chunks
- ChromaDB vector indexing and metadata tagging
- Longitudinal clinical timeline compilation and RAG-grounded longitudinal summarization

This phase establishes a decoupled task queue and worker abstraction that offloads these operations from HTTP request-response cycles into asynchronous background execution.

> [!IMPORTANT]
> All background operations strictly preserve patient data isolation and role-based access control (RBAC).
> Operational logs record task lifecycle events, task identifiers, and performance metrics, but NEVER raw protected health information (PHI), chunk text, or credentials.

---

## 2. Architecture Overview

```
                          FastAPI REST Clients
                                   |
                                   v
             +-------------------------------------------+
             |         Background Task Endpoints         |
             |       POST /api/v1/tasks/documents/...    |
             |       POST /api/v1/tasks/timeline/...     |
             |       GET  /api/v1/tasks/{task_id}        |
             |       GET  /api/v1/tasks                  |
             +-------------------------------------------+
                                   |
                                   v
             +-------------------------------------------+
             |           Task Service & RBAC             |
             |  - Patient clinical access validation     |
             |  - Idempotency guards (active duplicates) |
             |  - Task ownership & permission checking   |
             +-------------------------------------------+
                                   |
                                   v
             +-------------------------------------------+
             |     BaseBackgroundTaskProvider (ABC)      |
             +-------------------------------------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
+---------------------------------+         +---------------------------------+
|   LocalBackgroundTaskProvider   |         |   CeleryBackgroundTaskProvider  |
|  - In-memory thread-safe queue  |         |  - Optional Celery+Redis adapter|
|  - ThreadPoolExecutor workers   |         |  - Graceful fallback to local   |
|  - 100% offline & testable      |         |  - Safe credential handling     |
+---------------------------------+         +---------------------------------+
                                   |
                                   v
             +-------------------------------------------+
             |            Clinical Task Workers          |
             |  - Document processing & vector indexing  |
             |  - Longitudinal timeline compilation      |
             |  - Safety evaluation                      |
             +-------------------------------------------+
```

---

## 3. Task Lifecycle & States

```
[QUEUED] ───> [RUNNING] ───> [COMPLETED]
   |             |
   |             └───> [FAILED] ───> [RETRYING] ───> [QUEUED]
   |
   └───> [CANCELLED]
```

| State | Description |
|---|---|
| `QUEUED` | Task has been accepted and is waiting for an available worker thread. |
| `RUNNING` | Worker thread is actively executing the workload. Progress updated to > 0.0. |
| `COMPLETED` | Execution completed successfully. Results stored in `result_metadata`. |
| `FAILED` | Execution threw an exception. Sanitized failure message recorded in `error_message`. |
| `RETRYING` | Failed task was re-queued for execution up to `max_retries` attempts. |
| `CANCELLED` | Pending task was cancelled prior to completion upon authorized user request. |

---

## 4. Provider Abstraction

### `BaseBackgroundTaskProvider` (Abstract Interface)

Located in `app.ai.task_worker`:

```python
class BaseBackgroundTaskProvider(ABC):
    def submit_task(self, task_type, fn, fn_args, fn_kwargs, patient_id, created_by_user_id, payload, max_retries) -> BackgroundTask: ...
    def get_task(self, task_id: str) -> Optional[BackgroundTask]: ...
    def list_tasks(self, patient_id, created_by_user_id, status, task_type) -> list[BackgroundTask]: ...
    def cancel_task(self, task_id: str) -> bool: ...
    def retry_task(self, task_id: str) -> Optional[BackgroundTask]: ...
    def shutdown(self, wait: bool = True) -> None: ...
```

### Supported Provider Implementations

| Provider | `BACKGROUND_TASK_PROVIDER` | Description |
|---|---|---|
| `LocalBackgroundTaskProvider` | `local` (default) | In-memory thread-safe queue with `ThreadPoolExecutor`. Runs fully offline without Redis. |
| `SyncBackgroundTaskProvider` | `sync` | Inline synchronous execution for debugging and deterministic testing. |
| `CeleryBackgroundTaskProvider` | `celery` | Distributed task execution via Celery and Redis broker. Falls back safely if Redis/Celery is unavailable. |

---

## 5. Security & Patient Data Isolation

1. **Authorization & RBAC**:
   - `ADMIN` & `HEALTHCARE_STAFF`: Authorized to inspect all background tasks and enqueue processing.
   - `DOCTOR`: Authorized to inspect and enqueue tasks only for patients with active appointments or clinical encounters.
   - `PATIENT`: Strictly restricted to viewing only their own tasks (`task.patient_id == patient.patient_id`). Cannot trigger administrative document reprocessing tasks.
2. **Zero PHI in Operational Logs**:
   - Logs record `task_id`, `task_type`, `patient_id` (public ID only), duration, and status transitions.
   - Clinical document chunk contents, full-text extractions, and diagnostic details are never written to logs.
3. **Safe Error Sanitization**:
   - Unhandled worker exceptions are captured, truncated to 500 characters, and sanitized before returning to API clients.

---

## 6. REST API Endpoints

| Method | Endpoint | Access Level | Description |
|---|---|---|---|
| `POST` | `/api/v1/tasks/documents/{document_id}/process` | Doctors / Staff / Admin | Enqueue background document extraction & vector indexing |
| `POST` | `/api/v1/tasks/timeline/{patient_id}/summary` | Doctors / Staff / Admin | Enqueue background longitudinal timeline summary compilation |
| `GET` | `/api/v1/tasks/{task_id}` | Authenticated | Retrieve background task status, progress, and execution results |
| `GET` | `/api/v1/tasks` | Authenticated | List authorized background tasks with filtering and pagination |
| `POST` | `/api/v1/tasks/{task_id}/retry` | Doctors / Staff / Admin | Re-enqueue a failed or cancelled task |
| `POST` | `/api/v1/tasks/{task_id}/cancel` | Doctors / Staff / Admin | Cancel a pending background task |

---

## 7. Configuration

```bash
# Background Worker Configuration (Phase 9.0.3)
# Options: 'local' (offline thread pool, default — no Redis required)
#          'sync' (inline synchronous execution for test debugging)
#          'celery' (distributed Celery worker with Redis broker)
BACKGROUND_TASK_PROVIDER="local"
BACKGROUND_TASK_WORKERS=4

# Optional Celery Configuration
# CELERY_BROKER_URL="redis://localhost:6379/0"
# CELERY_RESULT_BACKEND="redis://localhost:6379/0"
```

---

## 8. Verification & Testing

The Phase 9.0.3 test suite (`backend/tests/test_tasks.py`) contains 22 tests verifying:
- Task ID generation and data validation
- In-memory lifecycle state transitions (QUEUED → RUNNING → COMPLETED / FAILED)
- Local thread pool asynchronous execution
- Task cancellation and retry mechanisms
- Celery provider fallback when broker is unconfigured or Celery is absent
- End-to-end document processing background task API integration
- Idempotency guards preventing duplicate active tasks
- RBAC authorization enforcement and cross-patient access rejection
- Credential safety and zero PHI in logs

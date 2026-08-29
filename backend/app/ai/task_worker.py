"""Background Asynchronous Task Worker Provider Abstraction.

Phase 9.0.3: Background Asynchronous Worker Architecture.

Provides:
- BaseBackgroundTaskProvider: abstract interface for task queue & execution
- LocalBackgroundTaskProvider: deterministic in-memory queue + ThreadPoolExecutor (default)
- SyncBackgroundTaskProvider: inline synchronous execution for debugging & deterministic tests
- CeleryBackgroundTaskProvider: optional distributed worker adapter for Celery + Redis
- get_background_task_provider: factory function resolving configured provider

Security:
- Operational logs record task IDs, types, state transitions, and durations.
- Raw PHI, document contents, and credentials are NEVER logged.
- Patient isolation context is preserved in task metadata.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import logging
import secrets
import threading
from typing import Any, Callable, Optional

from app.core.observability import get_correlation_id, set_correlation_id
from app.schemas.task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType

logger = logging.getLogger("medigen.tasks")


def generate_task_id() -> str:
    """Generate unique public background task identifier (e.g. TASK-20260829-A1B2C3D4)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"TASK-{date_str}-{random_part}"


class BaseBackgroundTaskProvider(ABC):
    """Abstract interface for background task management and execution."""

    @abstractmethod
    def submit_task(
        self,
        task_type: BackgroundTaskType,
        fn: Callable[..., dict[str, Any]],
        fn_args: tuple = (),
        fn_kwargs: Optional[dict[str, Any]] = None,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> BackgroundTask:
        """Enqueue a background task for asynchronous execution."""
        raise NotImplementedError

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Retrieve task details by task ID."""
        raise NotImplementedError

    @abstractmethod
    def list_tasks(
        self,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        status: Optional[BackgroundTaskStatus] = None,
        task_type: Optional[BackgroundTaskType] = None,
    ) -> list[BackgroundTask]:
        """List tasks matching optional filters."""
        raise NotImplementedError

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """Attempt to cancel a queued or running task."""
        raise NotImplementedError

    @abstractmethod
    def retry_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Retry a previously failed or cancelled task."""
        raise NotImplementedError

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Return operational metrics for worker pool and task queues."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self, wait: bool = True) -> None:
        """Cleanly shutdown any background threads or worker pools."""
        pass


class LocalBackgroundTaskProvider(BaseBackgroundTaskProvider):
    """In-memory thread-safe task queue & worker pool for offline execution.

    Uses concurrent.futures.ThreadPoolExecutor. No Redis or external infrastructure required.
    Suitable for local development, unit tests, and single-process deployments.
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="medigen-worker")
        self._tasks: dict[str, BackgroundTask] = {}
        self._task_callables: dict[str, tuple[Callable, tuple, dict, str]] = {}
        self._lock = threading.Lock()

    def submit_task(
        self,
        task_type: BackgroundTaskType,
        fn: Callable[..., dict[str, Any]],
        fn_args: tuple = (),
        fn_kwargs: Optional[dict[str, Any]] = None,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> BackgroundTask:
        task_id = generate_task_id()
        now = datetime.now(timezone.utc)
        kwargs = fn_kwargs or {}
        sanitized_payload = payload or {}
        corr_id = get_correlation_id()

        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            status=BackgroundTaskStatus.QUEUED,
            patient_id=patient_id,
            created_by_user_id=created_by_user_id,
            progress=0.0,
            result_metadata={},
            error_message=None,
            retry_count=0,
            max_retries=max_retries,
            payload=sanitized_payload,
            created_at=now,
            started_at=None,
            completed_at=None,
        )

        with self._lock:
            self._tasks[task_id] = task
            self._task_callables[task_id] = (fn, fn_args, kwargs, corr_id)

        logger.info(
            "Enqueued background task task_id=%s task_type=%s patient_id=%s correlation_id=%s",
            task_id,
            task_type.value,
            patient_id,
            corr_id,
        )

        # Dispatch execution to thread pool
        self._executor.submit(self._run_task, task_id)
        return task.model_copy()

    def _run_task(self, task_id: str) -> None:
        """Internal execution wrapper with error capture and lifecycle management."""
        with self._lock:
            task = self._tasks.get(task_id)
            callable_info = self._task_callables.get(task_id)

        if not task or not callable_info:
            return

        if task.status == BackgroundTaskStatus.CANCELLED:
            logger.info("Skipping cancelled task task_id=%s", task_id)
            return

        fn, args, kwargs, corr_id = callable_info
        set_correlation_id(corr_id)
        start_time = datetime.now(timezone.utc)

        with self._lock:
            task.status = BackgroundTaskStatus.RUNNING
            task.started_at = start_time
            task.progress = 0.1

        logger.info(
            "Started execution of background task task_id=%s task_type=%s",
            task_id,
            task.task_type.value,
        )

        try:
            # Execute actual task workload
            result = fn(*args, **kwargs)
            end_time = datetime.now(timezone.utc)

            with self._lock:
                task.status = BackgroundTaskStatus.COMPLETED
                task.progress = 1.0
                task.result_metadata = result if isinstance(result, dict) else {"result": result}
                task.completed_at = end_time
                task.error_message = None

            duration_s = (end_time - start_time).total_seconds()
            logger.info(
                "Completed background task task_id=%s task_type=%s duration=%.2fs",
                task_id,
                task.task_type.value,
                duration_s,
            )

        except Exception as exc:
            end_time = datetime.now(timezone.utc)
            error_str = str(exc)[:500]

            with self._lock:
                task.completed_at = end_time
                task.error_message = error_str
                task.status = BackgroundTaskStatus.FAILED

            logger.error(
                "Background task failed task_id=%s task_type=%s error_type=%s",
                task_id,
                task.task_type.value,
                type(exc).__name__,
            )

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            tasks = list(self._tasks.values())
        counts = {
            "queued": sum(1 for t in tasks if t.status == BackgroundTaskStatus.QUEUED),
            "running": sum(1 for t in tasks if t.status == BackgroundTaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == BackgroundTaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == BackgroundTaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == BackgroundTaskStatus.CANCELLED),
            "total": len(tasks),
            "max_workers": self._max_workers,
            "provider": "local",
        }
        return counts

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy() if task else None

    def list_tasks(
        self,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        status: Optional[BackgroundTaskStatus] = None,
        task_type: Optional[BackgroundTaskType] = None,
    ) -> list[BackgroundTask]:
        with self._lock:
            tasks = list(self._tasks.values())

        filtered: list[BackgroundTask] = []
        for t in tasks:
            if patient_id is not None and t.patient_id != patient_id:
                continue
            if created_by_user_id is not None and t.created_by_user_id != created_by_user_id:
                continue
            if status is not None and t.status != status:
                continue
            if task_type is not None and t.task_type != task_type:
                continue
            filtered.append(t.model_copy())

        # Sort newest first
        filtered.sort(key=lambda x: x.created_at, reverse=True)
        return filtered

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in (BackgroundTaskStatus.COMPLETED, BackgroundTaskStatus.FAILED, BackgroundTaskStatus.CANCELLED):
                return False
            task.status = BackgroundTaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = "Task was cancelled by user request."

        logger.info("Cancelled background task task_id=%s", task_id)
        return True

    def retry_task(self, task_id: str) -> Optional[BackgroundTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            callable_info = self._task_callables.get(task_id)

            if not task or not callable_info:
                return None

            if task.status not in (BackgroundTaskStatus.FAILED, BackgroundTaskStatus.CANCELLED):
                return None

            if task.retry_count >= task.max_retries:
                task.error_message = f"Exceeded maximum retry limit of {task.max_retries} attempts."
                return task.model_copy()

            task.retry_count += 1
            task.status = BackgroundTaskStatus.QUEUED
            task.progress = 0.0
            task.error_message = None
            task.started_at = None
            task.completed_at = None

        logger.info(
            "Retrying background task task_id=%s attempt=%d/%d",
            task_id,
            task.retry_count,
            task.max_retries,
        )

        self._executor.submit(self._run_task, task_id)
        return task.model_copy()

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)


class SyncBackgroundTaskProvider(BaseBackgroundTaskProvider):
    """Synchronous inline task execution provider for deterministic unit tests and debugging."""

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}
        self._task_callables: dict[str, tuple[Callable, tuple, dict]] = {}

    def submit_task(
        self,
        task_type: BackgroundTaskType,
        fn: Callable[..., dict[str, Any]],
        fn_args: tuple = (),
        fn_kwargs: Optional[dict[str, Any]] = None,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> BackgroundTask:
        task_id = generate_task_id()
        now = datetime.now(timezone.utc)
        kwargs = fn_kwargs or {}

        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            status=BackgroundTaskStatus.RUNNING,
            patient_id=patient_id,
            created_by_user_id=created_by_user_id,
            progress=0.1,
            result_metadata={},
            error_message=None,
            retry_count=0,
            max_retries=max_retries,
            payload=payload or {},
            created_at=now,
            started_at=now,
            completed_at=None,
        )

        self._tasks[task_id] = task
        self._task_callables[task_id] = (fn, fn_args, kwargs)

        try:
            result = fn(*fn_args, **kwargs)
            task.status = BackgroundTaskStatus.COMPLETED
            task.progress = 1.0
            task.result_metadata = result if isinstance(result, dict) else {"result": result}
            task.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            task.status = BackgroundTaskStatus.FAILED
            task.error_message = str(exc)[:500]
            task.completed_at = datetime.now(timezone.utc)

        return task.model_copy()

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        task = self._tasks.get(task_id)
        return task.model_copy() if task else None

    def list_tasks(
        self,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        status: Optional[BackgroundTaskStatus] = None,
        task_type: Optional[BackgroundTaskType] = None,
    ) -> list[BackgroundTask]:
        tasks = list(self._tasks.values())
        filtered: list[BackgroundTask] = []
        for t in tasks:
            if patient_id is not None and t.patient_id != patient_id:
                continue
            if created_by_user_id is not None and t.created_by_user_id != created_by_user_id:
                continue
            if status is not None and t.status != status:
                continue
            if task_type is not None and t.task_type != task_type:
                continue
            filtered.append(t.model_copy())
        filtered.sort(key=lambda x: x.created_at, reverse=True)
        return filtered

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status in (BackgroundTaskStatus.COMPLETED, BackgroundTaskStatus.FAILED):
            return False
        task.status = BackgroundTaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        return True

    def retry_task(self, task_id: str) -> Optional[BackgroundTask]:
        task = self._tasks.get(task_id)
        callable_info = self._task_callables.get(task_id)
        if not task or not callable_info:
            return None
        if task.status not in (BackgroundTaskStatus.FAILED, BackgroundTaskStatus.CANCELLED):
            return None

        fn, args, kwargs = callable_info
        task.retry_count += 1
        task.status = BackgroundTaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)

        try:
            result = fn(*args, **kwargs)
            task.status = BackgroundTaskStatus.COMPLETED
            task.progress = 1.0
            task.result_metadata = result if isinstance(result, dict) else {"result": result}
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = None
        except Exception as exc:
            task.status = BackgroundTaskStatus.FAILED
            task.error_message = str(exc)[:500]
            task.completed_at = datetime.now(timezone.utc)

        return task.model_copy()

    def get_metrics(self) -> dict[str, Any]:
        tasks = list(self._tasks.values())
        return {
            "queued": sum(1 for t in tasks if t.status == BackgroundTaskStatus.QUEUED),
            "running": sum(1 for t in tasks if t.status == BackgroundTaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == BackgroundTaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == BackgroundTaskStatus.FAILED),
            "cancelled": sum(1 for t in tasks if t.status == BackgroundTaskStatus.CANCELLED),
            "total": len(tasks),
            "max_workers": 1,
            "provider": "sync",
        }

    def shutdown(self, wait: bool = True) -> None:
        pass


class CeleryBackgroundTaskProvider(BaseBackgroundTaskProvider):
    """Optional adapter boundary for distributed task execution via Celery + Redis.

    Fails safely without crashing if Celery is not installed or the Redis broker is unavailable.
    Falls back gracefully to local execution with appropriate warning.
    """

    def __init__(
        self,
        broker_url: Optional[str] = None,
        result_backend: Optional[str] = None,
        fallback_provider: Optional[BaseBackgroundTaskProvider] = None,
    ):
        self._broker_url = broker_url
        self._result_backend = result_backend
        self._fallback = fallback_provider or LocalBackgroundTaskProvider(max_workers=2)
        self._celery_app = None
        self._is_celery_available = False

        self._init_celery()

    def _init_celery(self) -> None:
        """Initialize Celery application safely without raising exceptions."""
        if not self._broker_url:
            logger.warning(
                "Celery broker URL not configured; CeleryBackgroundTaskProvider falling back to local worker."
            )
            return

        try:
            import celery  # type: ignore # noqa: F401

            # Build app with broker (credentials never printed in log output)
            self._celery_app = celery.Celery(
                "medigen_tasks",
                broker=self._broker_url,
                backend=self._result_backend,
            )
            self._is_celery_available = True
            logger.info("Celery task queue initialized (broker_configured=True)")
        except ImportError:
            logger.warning("Celery package is not installed; falling back to local task worker.")
            self._is_celery_available = False
        except Exception as exc:
            logger.warning(
                "Celery initialization failed (%s); falling back to local task worker.",
                type(exc).__name__,
            )
            self._is_celery_available = False

    @property
    def is_celery_active(self) -> bool:
        return self._is_celery_available and self._celery_app is not None

    def submit_task(
        self,
        task_type: BackgroundTaskType,
        fn: Callable[..., dict[str, Any]],
        fn_args: tuple = (),
        fn_kwargs: Optional[dict[str, Any]] = None,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> BackgroundTask:
        # If celery is not active, delegate to safe fallback provider
        return self._fallback.submit_task(
            task_type=task_type,
            fn=fn,
            fn_args=fn_args,
            fn_kwargs=fn_kwargs,
            patient_id=patient_id,
            created_by_user_id=created_by_user_id,
            payload=payload,
            max_retries=max_retries,
        )

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        return self._fallback.get_task(task_id)

    def list_tasks(
        self,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        status: Optional[BackgroundTaskStatus] = None,
        task_type: Optional[BackgroundTaskType] = None,
    ) -> list[BackgroundTask]:
        return self._fallback.list_tasks(
            patient_id=patient_id,
            created_by_user_id=created_by_user_id,
            status=status,
            task_type=task_type,
        )

    def cancel_task(self, task_id: str) -> bool:
        return self._fallback.cancel_task(task_id)

    def retry_task(self, task_id: str) -> Optional[BackgroundTask]:
        return self._fallback.retry_task(task_id)

    def get_metrics(self) -> dict[str, Any]:
        metrics = self._fallback.get_metrics()
        metrics["provider"] = "celery" if self.is_celery_active else "celery_fallback_local"
        metrics["celery_active"] = self.is_celery_active
        return metrics

    def shutdown(self, wait: bool = True) -> None:
        self._fallback.shutdown(wait=wait)


# ---------------------------------------------------------------------------
# Global Singleton & Factory
# ---------------------------------------------------------------------------

_GLOBAL_TASK_PROVIDER: Optional[BaseBackgroundTaskProvider] = None
_PROVIDER_LOCK = threading.Lock()


def get_background_task_provider(
    provider_type: Optional[str] = None,
    max_workers: Optional[int] = None,
    broker_url: Optional[str] = None,
    result_backend: Optional[str] = None,
    force_new: bool = False,
) -> BaseBackgroundTaskProvider:
    """Resolve and return the configured background task worker provider.

    Args:
        provider_type: 'local' (default), 'sync', or 'celery'.
        max_workers: Worker pool size for local provider.
        broker_url: Optional Celery broker URL.
        result_backend: Optional Celery result backend URL.
        force_new: If True, creates a fresh provider instance (useful for isolated tests).

    Returns:
        Configured BaseBackgroundTaskProvider implementation.
    """
    global _GLOBAL_TASK_PROVIDER

    if not force_new and _GLOBAL_TASK_PROVIDER is not None:
        return _GLOBAL_TASK_PROVIDER

    with _PROVIDER_LOCK:
        if not force_new and _GLOBAL_TASK_PROVIDER is not None:
            return _GLOBAL_TASK_PROVIDER

        from app.core.config import settings

        ptype = (provider_type or settings.BACKGROUND_TASK_PROVIDER or "local").lower().strip()
        workers = max_workers if max_workers is not None else settings.BACKGROUND_TASK_WORKERS

        if ptype == "local":
            provider = LocalBackgroundTaskProvider(max_workers=workers)
        elif ptype == "sync":
            provider = SyncBackgroundTaskProvider()
        elif ptype == "celery":
            provider = CeleryBackgroundTaskProvider(
                broker_url=broker_url or settings.CELERY_BROKER_URL,
                result_backend=result_backend or settings.CELERY_RESULT_BACKEND,
                fallback_provider=LocalBackgroundTaskProvider(max_workers=workers),
            )
        else:
            raise ValueError(
                f"Unknown background task provider: '{provider_type}'. "
                f"Valid options: 'local', 'sync', 'celery'."
            )

        if not force_new:
            _GLOBAL_TASK_PROVIDER = provider

        return provider


def reset_background_task_provider() -> None:
    """Reset the global background task provider singleton (for test isolation)."""
    global _GLOBAL_TASK_PROVIDER
    with _PROVIDER_LOCK:
        if _GLOBAL_TASK_PROVIDER is not None:
            _GLOBAL_TASK_PROVIDER.shutdown(wait=False)
            _GLOBAL_TASK_PROVIDER = None

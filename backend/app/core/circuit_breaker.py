"""Circuit Breaker & Resilience Pattern for External Integrations.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Provides:
- CircuitBreaker: state machine managing CLOSED, OPEN, and HALF_OPEN transitions
- Protection for external Cloud LLMs, OCR services, and OpenFDA APIs
- Strict non-retry policy for clinical mutations to maintain idempotency
- Fallback invocation when circuits are open or tripped
"""

from enum import Enum
import functools
import logging
import threading
import time
from typing import Any, Callable, Optional, Type

logger = logging.getLogger("medigen.resilience")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal healthy operation; requests pass through
    OPEN = "OPEN"            # Tripped; requests immediately fail or invoke fallback
    HALF_OPEN = "HALF_OPEN"  # Testing external service recovery with limited probe requests


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit breaker is in an OPEN state."""

    def __init__(self, name: str, retry_after_seconds: float):
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. Service temporarily unavailable. Retry in {retry_after_seconds:.1f}s."
        )
        self.name = name
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    """Thread-safe circuit breaker implementation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 2,
        expected_exceptions: tuple[Type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and (time.time() - self._last_failure_time >= self.recovery_timeout):
                    logger.info("Circuit breaker '%s' transition: OPEN -> HALF_OPEN (probing)", self.name)
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
            return self._state

    def call(self, fn: Callable[..., Any], *args: Any, fallback: Optional[Callable[..., Any]] = None, **kwargs: Any) -> Any:
        """Execute callable `fn` protected by the circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            retry_after = max(1.0, self.recovery_timeout - (time.time() - (self._last_failure_time or time.time())))
            logger.warning(
                "Circuit breaker '%s' is OPEN. Blocking execution. Retry after %.1fs",
                self.name,
                retry_after,
            )
            if fallback:
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpenException(self.name, retry_after)

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as exc:
            self._on_failure(exc)
            if fallback:
                logger.info("Circuit breaker '%s' failure caught (%s). Executing fallback.", self.name, exc)
                return fallback(*args, **kwargs)
            raise

    def _on_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_success_threshold:
                    logger.info("Circuit breaker '%s' recovered: HALF_OPEN -> CLOSED", self.name)
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            logger.warning(
                "Circuit breaker '%s' failure #%d: %s (type=%s)",
                self.name,
                self._failure_count,
                exc,
                type(exc).__name__,
            )

            if self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker '%s' probe failed: HALF_OPEN -> OPEN", self.name)
                self._state = CircuitState.OPEN
            elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
                logger.error(
                    "Circuit breaker '%s' threshold reached (%d failures): CLOSED -> OPEN",
                    self.name,
                    self._failure_count,
                )
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Force reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
            }


# Registry of active named circuit breakers
_CIRCUIT_BREAKERS: dict[str, CircuitBreaker] = {}
_REGISTRY_LOCK = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Retrieve or create a named singleton circuit breaker."""
    with _REGISTRY_LOCK:
        if name not in _CIRCUIT_BREAKERS:
            _CIRCUIT_BREAKERS[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
        return _CIRCUIT_BREAKERS[name]


def circuit_breaker(name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0, fallback: Optional[Callable] = None):
    """Decorator wrapping a function with named circuit breaker protection."""

    def decorator(fn: Callable):
        cb = get_circuit_breaker(name, failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return cb.call(fn, *args, fallback=fallback, **kwargs)

        return wrapper

    return decorator

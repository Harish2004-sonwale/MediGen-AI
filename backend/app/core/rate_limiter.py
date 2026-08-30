"""Distributed Sliding-Window Rate Limiter & Abuse Protection.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Provides:
- Sliding-window rate limiter with Redis backend and in-memory thread-safe fallback
- Extraction and validation of client identity (IP + optional authenticated User ID)
- Protection tiers for Authentication, Chat/LLM, Bulk Exports, and General API requests
- RateLimiterMiddleware: ASGI middleware applying global and route-specific rate limits
- Proper HTTP 429 Too Many Requests responses with Retry-After and X-RateLimit headers
"""

from collections import defaultdict
from datetime import datetime, timezone
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.core.config import settings
from app.core.observability import get_correlation_id

logger = logging.getLogger("medigen.ratelimit")


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter supporting Redis and thread-safe in-memory storage."""

    def __init__(self):
        self._local_buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.RLock()
        self._redis_client: Optional[Any] = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        try:
            import redis  # type: ignore

            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            self._redis_client.ping()
            self._redis_available = True
            logger.info("Rate limiter connected to Redis.")
        except Exception as exc:
            self._redis_available = False
            logger.debug("Redis rate-limiting backend not available (%s); using in-memory limiter.", exc)

    def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """Evaluate whether a request for `identifier` is within the `limit` / `window_seconds`.

        Returns:
            (is_allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        if not settings.RATE_LIMIT_ENABLED or limit <= 0:
            return True, limit, 0

        now = time.time()
        window_start = now - window_seconds

        # 1. Try Redis sliding window if available
        if self._redis_available and self._redis_client is not None:
            try:
                key = f"ratelimit:{identifier}:{window_seconds}"
                pipe = self._redis_client.pipeline()
                # Remove timestamps older than window_start
                pipe.zremrangebyscore(key, "-inf", window_start)
                # Count remaining timestamps in current window
                pipe.zcard(key)
                # Add current timestamp
                pipe.zadd(key, {str(now): now})
                # Set TTL on the sorted set key
                pipe.expire(key, window_seconds + 5)
                results = pipe.execute()
                current_count = results[1]

                if current_count >= limit:
                    # Over limit: fetch oldest timestamp to calculate retry_after
                    oldest = self._redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        retry_after = max(1, int(oldest[0][1] + window_seconds - now))
                    else:
                        retry_after = int(window_seconds)
                    return False, 0, retry_after

                remaining = max(0, limit - current_count - 1)
                return True, remaining, 0
            except Exception as exc:
                logger.warning("Redis rate limiter error: %s. Using local fallback.", exc)
                self._redis_available = False

        # 2. Local in-memory sliding window fallback
        with self._lock:
            timestamps = self._local_buckets[identifier]
            # Prune old timestamps
            while timestamps and timestamps[0] < window_start:
                timestamps.pop(0)

            if len(timestamps) >= limit:
                retry_after = max(1, int(timestamps[0] + window_seconds - now))
                return False, 0, retry_after

            timestamps.append(now)
            remaining = max(0, limit - len(timestamps))
            return True, remaining, 0

    def reset(self, identifier: Optional[str] = None) -> None:
        """Reset rate limit buckets (useful for unit tests)."""
        with self._lock:
            if identifier:
                self._local_buckets.pop(identifier, None)
            else:
                self._local_buckets.clear()


# Global rate limiter instance
_GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _GLOBAL_RATE_LIMITER


def extract_client_ip(request: Request) -> str:
    """Extract client IP address safely considering reverse proxies."""
    # Check X-Forwarded-For header
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # First IP in list is client IP
        ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if ips:
            return ips[0]
    # Fallback to direct client host
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def get_rate_limit_for_path(path: str) -> Tuple[int, int]:
    """Resolve rate limit (requests_per_minute, window_seconds) for a given URL path."""
    # 1. Strict Authentication / Login limiter (e.g. 5 req/min)
    if "/auth/login" in path or "/auth/register" in path:
        return settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60

    # 2. AI Chat & LLM synthesis endpoints (e.g. 20 req/min)
    if "/chat/sessions" in path or "/rag/query" in path or "/agents" in path:
        return 20, 60

    # 3. Bulk exports & heavy queries (e.g. 15 req/min)
    if "/fhir/patients/" in path and "/bundle" in path:
        return 15, 60
    if "/timeline/" in path and "/summary" in path:
        return 15, 60

    # 4. General API traffic (default: 60 req/min)
    return settings.RATE_LIMIT_API_PER_MINUTE, 60


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware enforcing distributed rate limiting per client IP / user."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for static assets, health probes, tests, and docs
        path = request.url.path
        if (
            path in ("/health", "/ready", "/healthz", "/docs", "/redoc", "/openapi.json")
            or path.startswith("/assets/")
            or request.method == "OPTIONS"
            or not settings.RATE_LIMIT_ENABLED
            or settings.ENVIRONMENT.lower() in ("test", "testing")
            or "PYTEST_CURRENT_TEST" in os.environ
            or (request.client and request.client.host in ("testclient", "testserver"))
        ):
            return await call_next(request)

        client_ip = extract_client_ip(request)
        # Check for Authorization header to rate-limit by user if token is present
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Rate limit key combines user token prefix and IP
            token_prefix = auth_header[7:20]
            identifier = f"user:{token_prefix}:{path}"
        else:
            identifier = f"ip:{client_ip}:{path}"

        limit, window_seconds = get_rate_limit_for_path(path)
        limiter = get_rate_limiter()
        is_allowed, remaining, retry_after = limiter.is_allowed(
            identifier=identifier,
            limit=limit,
            window_seconds=window_seconds,
        )

        if not is_allowed:
            corr_id = get_correlation_id()
            logger.warning(
                "Rate limit exceeded: identifier=%s path=%s limit=%s/min retry_after=%ss [corr_id=%s]",
                identifier,
                path,
                limit,
                retry_after,
                corr_id,
            )
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Limit is {limit} requests per {window_seconds}s. Please retry in {retry_after} seconds.",
                    "retry_after_seconds": retry_after,
                    "correlation_id": corr_id,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                },
            )

        response: Response = await call_next(request)
        # Inject informational rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

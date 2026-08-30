"""Distributed Redis Caching Layer with In-Memory Fallback.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Provides:
- BaseCache: abstract caching interface
- RedisCache: production distributed cache using redis-py connection pooling
- InMemoryCache: deterministic in-memory LRU fallback for test & development
- get_cache: singleton factory resolving active cache provider
- safe_cached: decorator for caching non-sensitive deterministic computations
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import functools
import json
import logging
import threading
import time
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger("medigen.cache")


class BaseCache(ABC):
    """Abstract caching interface for distributed and local caching."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key. Returns None if missing or expired."""
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store a value with an optional TTL in seconds."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove a cached key."""
        raise NotImplementedError

    @abstractmethod
    def clear(self, prefix: Optional[str] = None) -> bool:
        """Flush all keys or all keys matching an optional namespace prefix."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if cache backend is healthy and responding."""
        raise NotImplementedError


class InMemoryCache(BaseCache):
    """Thread-safe in-memory cache with TTL expiration.

    Used as the default in development, unit tests, and as an offline fallback.
    """

    def __init__(self, default_ttl: int = 3600):
        self._store: dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            val, expiry = self._store[key]
            if expiry is not None and time.time() > expiry:
                del self._store[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            expiry = time.time() + ttl if ttl and ttl > 0 else None
            self._store[key] = (value, expiry)
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self, prefix: Optional[str] = None) -> bool:
        with self._lock:
            if not prefix:
                self._store.clear()
                return True
            keys_to_del = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_del:
                del self._store[k]
            return True

    def is_available(self) -> bool:
        return True


class RedisCache(BaseCache):
    """Production distributed cache connecting to Redis.

    Gracefully falls back to InMemoryCache if Redis server is unreachable.
    """

    def __init__(self, redis_url: str, default_ttl: int = 3600):
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._client: Optional[Any] = None
        self._fallback = InMemoryCache(default_ttl=default_ttl)
        self._redis_available = False
        self._init_client()

    def _init_client(self) -> None:
        try:
            import redis  # type: ignore

            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            self._client.ping()
            self._redis_available = True
            logger.info("RedisCache connected successfully to %s", settings.safe_dump().get("REDIS_URL"))
        except Exception as exc:
            self._redis_available = False
            logger.warning("Redis unavailable (%s). Falling back to InMemoryCache.", exc)

    def is_available(self) -> bool:
        if not self._redis_available or self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            self._redis_available = False
            return False

    def get(self, key: str) -> Optional[Any]:
        if not self._redis_available or self._client is None:
            return self._fallback.get(key)
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except Exception as exc:
            logger.warning("Redis error on get(%s): %s. Falling back to local cache.", key, exc)
            return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        if not self._redis_available or self._client is None:
            return self._fallback.set(key, value, ttl_seconds=ttl)
        try:
            serialized = json.dumps(value) if not isinstance(value, (str, int, float, bool)) else str(value)
            if ttl and ttl > 0:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
            # Also keep fallback in sync
            self._fallback.set(key, value, ttl_seconds=ttl)
            return True
        except Exception as exc:
            logger.warning("Redis error on set(%s): %s. Writing to local fallback.", key, exc)
            return self._fallback.set(key, value, ttl_seconds=ttl)

    def delete(self, key: str) -> bool:
        self._fallback.delete(key)
        if not self._redis_available or self._client is None:
            return True
        try:
            return bool(self._client.delete(key))
        except Exception as exc:
            logger.warning("Redis error on delete(%s): %s", key, exc)
            return True

    def clear(self, prefix: Optional[str] = None) -> bool:
        self._fallback.clear(prefix)
        if not self._redis_available or self._client is None:
            return True
        try:
            if not prefix:
                self._client.flushdb()
            else:
                keys = self._client.keys(f"{prefix}*")
                if keys:
                    self._client.delete(*keys)
            return True
        except Exception as exc:
            logger.warning("Redis error on clear(prefix=%s): %s", prefix, exc)
            return True


# Singleton cache instance
_GLOBAL_CACHE: Optional[BaseCache] = None
_CACHE_LOCK = threading.Lock()


def get_cache() -> BaseCache:
    """Retrieve global cache instance configured according to application settings."""
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        with _CACHE_LOCK:
            if _GLOBAL_CACHE is None:
                if not settings.CACHE_ENABLED:
                    _GLOBAL_CACHE = InMemoryCache(default_ttl=settings.CACHE_TTL_SECONDS)
                else:
                    try:
                        _GLOBAL_CACHE = RedisCache(
                            redis_url=settings.REDIS_URL,
                            default_ttl=settings.CACHE_TTL_SECONDS,
                        )
                    except Exception:
                        _GLOBAL_CACHE = InMemoryCache(default_ttl=settings.CACHE_TTL_SECONDS)
    return _GLOBAL_CACHE


def reset_cache_for_testing() -> None:
    """Reset global cache instance (useful for unit testing isolation)."""
    global _GLOBAL_CACHE
    with _CACHE_LOCK:
        _GLOBAL_CACHE = None


def cached(prefix: str, ttl_seconds: int = 3600) -> Callable:
    """Decorator to cache function results by hash of arguments.

    Only use for pure, non-PHI deterministic lookups (e.g. drug interactions, terminologies, CQM definitions).
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            cache = get_cache()
            arg_key = f"{args}:{sorted(kwargs.items())}"
            cache_key = f"{prefix}:{hash(arg_key)}"
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val
            result = fn(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl_seconds=ttl_seconds)
            return result

        return wrapper

    return decorator

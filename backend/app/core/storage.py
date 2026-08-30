"""Pluggable Storage Abstraction for Clinical Documents and Imaging Assets.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Provides:
- StorageProvider: abstract interface for blob and file management
- LocalStorageProvider: local filesystem storage with path isolation (default)
- S3StorageProvider: AWS S3 & MinIO S3-compatible cloud storage with pre-signed URLs
- MockStorageProvider: in-memory storage provider for deterministic unit testing
- get_storage_provider: factory function resolving configured storage backend
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import io
import logging
import os
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

from app.core.config import settings

logger = logging.getLogger("medigen.storage")


class StorageProvider(ABC):
    """Abstract base class for clinical document & media file storage."""

    @abstractmethod
    def save_file(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> str:
        """Save file content and return the persistent key / identifier."""
        raise NotImplementedError

    @abstractmethod
    def read_file(self, key: str) -> bytes:
        """Read and return complete file content as bytes."""
        raise NotImplementedError

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """Delete file at key. Returns True if deleted or already absent."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if a file exists at the given key."""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self, key: str) -> dict[str, Any]:
        """Return metadata for the file (size_bytes, content_type, updated_at, sha256)."""
        raise NotImplementedError

    @abstractmethod
    def get_url(self, key: str, expiry_seconds: int = 3600) -> str:
        """Generate a direct or pre-signed access URL for the file."""
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: Optional[str] = None):
        self._base_dir = Path(base_dir or os.getcwd())

    def _resolve_path(self, key: str) -> Path:
        # Prevent directory traversal attacks
        clean_key = os.path.normpath(key).lstrip("/\\")
        full_path = self._base_dir / clean_key
        return full_path

    def save_file(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> str:
        path = self._resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_bytes = data if isinstance(data, bytes) else data.read()
        with open(path, "wb") as f:
            f.write(raw_bytes)
        return str(key)

    def read_file(self, key: str) -> bytes:
        path = self._resolve_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Storage file not found: {key}")
        with open(path, "rb") as f:
            return f.read()

    def delete_file(self, key: str) -> bool:
        path = self._resolve_path(key)
        if path.is_file():
            try:
                path.unlink()
                return True
            except OSError as exc:
                logger.error("Failed to delete local storage file %s: %s", key, exc)
                return False
        return True

    def exists(self, key: str) -> bool:
        return self._resolve_path(key).is_file()

    def get_metadata(self, key: str) -> dict[str, Any]:
        path = self._resolve_path(key)
        if not path.is_file():
            raise FileNotFoundError(f"Storage file not found: {key}")
        stat = path.stat()
        raw_bytes = self.read_file(key)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        return {
            "key": key,
            "size_bytes": stat.st_size,
            "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": sha256,
            "storage_provider": "local",
        }

    def get_url(self, key: str, expiry_seconds: int = 3600) -> str:
        # For local storage, returns the relative API path
        return f"/api/v1/files/{key}"


class S3StorageProvider(StorageProvider):
    """AWS S3 and MinIO S3-compatible cloud object storage provider."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self._bucket = bucket_name
        self._endpoint_url = endpoint_url
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key
        self._client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import boto3  # type: ignore

            kwargs: dict[str, Any] = {"region_name": self._region}
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            if self._access_key and self._secret_key:
                kwargs["aws_access_key_id"] = self._access_key
                kwargs["aws_secret_access_key"] = self._secret_key

            self._client = boto3.client("s3", **kwargs)
            logger.info("S3StorageProvider initialized for bucket: %s", self._bucket)
        except Exception as exc:
            logger.warning("Could not initialize S3 client: %s", exc)
            self._client = None

    def save_file(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> str:
        if self._client is None:
            raise RuntimeError("S3 client is not configured")
        raw_bytes = data if isinstance(data, bytes) else data.read()
        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=raw_bytes,
            **extra_args,
        )
        return key

    def read_file(self, key: str) -> bytes:
        if self._client is None:
            raise RuntimeError("S3 client is not configured")
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def delete_file(self, key: str) -> bool:
        if self._client is None:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except Exception as exc:
            logger.error("Error deleting S3 object %s: %s", key, exc)
            return False

    def exists(self, key: str) -> bool:
        if self._client is None:
            return False
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def get_metadata(self, key: str) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("S3 client is not configured")
        head = self._client.head_object(Bucket=self._bucket, Key=key)
        return {
            "key": key,
            "size_bytes": head.get("ContentLength", 0),
            "content_type": head.get("ContentType", "application/octet-stream"),
            "updated_at": head.get("LastModified", datetime.now(timezone.utc)).isoformat(),
            "etag": head.get("ETag", "").strip('"'),
            "storage_provider": "s3",
        }

    def get_url(self, key: str, expiry_seconds: int = 3600) -> str:
        if self._client is None:
            return f"s3://{self._bucket}/{key}"
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expiry_seconds,
            )
            return str(url)
        except Exception as exc:
            logger.warning("Error generating S3 pre-signed URL: %s", exc)
            return f"s3://{self._bucket}/{key}"


class MockStorageProvider(StorageProvider):
    """In-memory mock storage provider for fast, deterministic unit testing."""

    def __init__(self):
        self._store: dict[str, tuple[bytes, Optional[str], datetime]] = {}

    def save_file(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
    ) -> str:
        raw_bytes = data if isinstance(data, bytes) else data.read()
        self._store[key] = (raw_bytes, content_type, datetime.now(timezone.utc))
        return key

    def read_file(self, key: str) -> bytes:
        if key not in self._store:
            raise FileNotFoundError(f"Mock storage key not found: {key}")
        return self._store[key][0]

    def delete_file(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return True

    def exists(self, key: str) -> bool:
        return key in self._store

    def get_metadata(self, key: str) -> dict[str, Any]:
        if key not in self._store:
            raise FileNotFoundError(f"Mock storage key not found: {key}")
        raw, ctype, updated = self._store[key]
        sha256 = hashlib.sha256(raw).hexdigest()
        return {
            "key": key,
            "size_bytes": len(raw),
            "content_type": ctype or "application/octet-stream",
            "updated_at": updated.isoformat(),
            "sha256": sha256,
            "storage_provider": "mock",
        }

    def get_url(self, key: str, expiry_seconds: int = 3600) -> str:
        return f"mock://storage/{key}?expires_in={expiry_seconds}"


# Factory singleton resolver
_GLOBAL_STORAGE_PROVIDER: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """Resolve the active StorageProvider based on application settings."""
    global _GLOBAL_STORAGE_PROVIDER
    if _GLOBAL_STORAGE_PROVIDER is None:
        provider_name = settings.STORAGE_PROVIDER.lower()
        if provider_name == "s3":
            _GLOBAL_STORAGE_PROVIDER = S3StorageProvider(
                bucket_name=settings.S3_BUCKET_NAME,
                endpoint_url=settings.S3_ENDPOINT_URL,
                region=settings.S3_REGION,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
            )
        elif provider_name == "mock":
            _GLOBAL_STORAGE_PROVIDER = MockStorageProvider()
        else:
            _GLOBAL_STORAGE_PROVIDER = LocalStorageProvider()
    return _GLOBAL_STORAGE_PROVIDER


def set_storage_provider(provider: StorageProvider) -> None:
    """Override active storage provider (useful for test isolation)."""
    global _GLOBAL_STORAGE_PROVIDER
    _GLOBAL_STORAGE_PROVIDER = provider

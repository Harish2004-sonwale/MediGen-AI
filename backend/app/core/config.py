from typing import Any
import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MediGen AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # 'development' | 'staging' | 'production' | 'test'
    DEBUG: bool = True
    HOST: str = "0.0.0.0"  # nosec B104
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    ASGI_WORKERS: int = 1
    CORS_ORIGINS: str = "*"  # Comma-separated or JSON list of origins: "https://app.medigen.ai,https://admin.medigen.ai"

    # PostgreSQL Database Configuration
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/medigen_ai"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_CONNECT_TIMEOUT: int = 5

    # JWT & Authentication Configuration
    JWT_SECRET_KEY: str = (
        "YOUR_JWT_SECRET_KEY_KEEP_IT_SECRET_CHANGE_IN_PRODUCTION"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Medical Document Storage & Chunking Configuration
    DOCUMENT_STORAGE_PATH: str = "data/medical_documents"
    MAX_DOCUMENT_SIZE_MB: int = 10
    DOCUMENT_CHUNK_SIZE_TOKENS: int = 500
    DOCUMENT_CHUNK_OVERLAP_TOKENS: int = 100

    # Vector Database & Embedding Configuration (Phase 8.4)
    EMBEDDING_PROVIDER: str = "mock"
    EMBEDDING_DIMENSION: int = 384
    VECTOR_DB_PATH: str = "data/vector_db"
    VECTOR_COLLECTION_NAME: str = "medical_documents"
    VECTOR_TOP_K: int = 5

    # Clinical RAG & LLM Configuration (Phase 8.5, 8.6 & 8.8)
    RAG_TOP_K: int = 5
    RAG_MIN_SIMILARITY: float = 0.0
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "medigen-clinical-v1"
    RAG_MAX_CONTEXT_CHUNKS: int = 10
    CHAT_HISTORY_MAX_TURNS: int = 5
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"


    # Pluggable OCR Configuration (Phase 8.8)
    OCR_ENABLED: bool = False
    OCR_PROVIDER: str = "mock"

    # AWS & Bedrock Configuration (Phase 8.8)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"

    # Drug Knowledge Base Configuration (Phase 9.0.2)
    # Options: 'mock' (offline, default) | 'openfda' (optional external FDA API)
    DRUG_KNOWLEDGE_PROVIDER: str = "mock"
    OPENFDA_API_KEY: str | None = None
    OPENFDA_TIMEOUT_SECONDS: int = 5

    # Background Asynchronous Worker Configuration (Phase 9.0.3)
    # Options: 'local' (offline thread pool, default) | 'sync' (inline synchronous for test debugging) | 'celery' (distributed Celery+Redis)
    BACKGROUND_TASK_PROVIDER: str = "local"
    BACKGROUND_TASK_WORKERS: int = 4
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Production Observability & Monitoring Configuration (Phase 9.0.4)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # 'text' | 'json'
    METRICS_ENABLED: bool = True

    # Multi-Modal Medical Diagnostics & Imaging Configuration (Phase 9.0.7)
    MEDIA_STORAGE_DIR: str = "data/medical_media"
    MEDIA_MAX_FILE_SIZE_BYTES: int = 52428800  # 50 MB
    IMAGING_PROVIDER: str = "mock"

    # Distributed Redis & Caching Configuration (Phase 9.0.20)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 3600

    # Rate Limiting & Abuse Protection (Phase 9.0.20)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 5
    RATE_LIMIT_API_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 20

    # Pluggable Storage & Object Storage Configuration (Phase 9.0.20)
    # Options: 'local' (default) | 's3' (AWS S3 / MinIO) | 'mock'
    STORAGE_PROVIDER: str = "local"
    S3_BUCKET_NAME: str = "medigen-clinical-storage"
    S3_ENDPOINT_URL: str | None = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    # Prometheus Metrics & Observability (Phase 9.0.20)
    PROMETHEUS_METRICS_ENABLED: bool = True

    # Pluggable Audit Streaming & SIEM Integration (Phase 9.0.20)
    AUDIT_STREAMING_ENABLED: bool = False
    AUDIT_STREAMING_DESTINATION: str = "none"  # 'none' | 'syslog' | 'webhook' | 'cloudwatch'
    AUDIT_STREAMING_ENDPOINT: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS into a clean list of allowed origin URLs."""
        raw = self.CORS_ORIGINS.strip()
        if not raw or raw == "*":
            return ["*"]
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    def is_production(self) -> bool:
        """Return True if running in a hardened production or staging environment."""
        return self.ENVIRONMENT.lower() in ("production", "prod", "staging")

    def validate_production_settings(self) -> list[str]:
        """Validate critical configuration settings for production safety.

        Returns a list of error messages. If empty, the configuration is valid.
        """
        errors: list[str] = []
        if not self.is_production():
            return errors

        # 1. Insecure JWT Secret Key check
        if (
            not self.JWT_SECRET_KEY
            or "YOUR_JWT_SECRET_KEY" in self.JWT_SECRET_KEY
            or len(self.JWT_SECRET_KEY) < 32
        ):
            errors.append(
                "Insecure JWT_SECRET_KEY in production. Must be a cryptographically strong secret with at least 32 characters."
            )

        # 2. Insecure DEBUG check
        if self.DEBUG:
            errors.append(
                "DEBUG mode must be set to False in production environments."
            )

        # 3. Database URL placeholder check
        if "YOUR_POSTGRES_PASSWORD" in self.DATABASE_URL:
            errors.append(
                "DATABASE_URL contains placeholder password in production."
            )

        # 4. Production CORS wildcard warning / validation
        cors_origins = self.get_cors_origins()
        if "*" in cors_origins and self.is_production():
            errors.append(
                "CORS_ORIGINS cannot be wildcard '*' in production. Specify explicit allowed domains."
            )

        # 5. S3 Storage credentials if S3 provider is configured in production
        if self.STORAGE_PROVIDER == "s3" and (not self.S3_ACCESS_KEY or not self.S3_SECRET_KEY):
            errors.append(
                "S3_ACCESS_KEY and S3_SECRET_KEY must be provided when STORAGE_PROVIDER is 's3' in production."
            )

        return errors

    def safe_dump(self) -> dict[str, Any]:
        """Dump settings with all sensitive keys, tokens, and database passwords redacted."""
        raw = self.model_dump()
        sensitive_keys = {
            "JWT_SECRET_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "AWS_SECRET_ACCESS_KEY",
            "S3_SECRET_KEY",
            "S3_ACCESS_KEY",
            "OPENFDA_API_KEY",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
        }
        safe: dict[str, Any] = {}
        for k, v in raw.items():
            if k in sensitive_keys and v:
                safe[k] = "[REDACTED]"
            elif k == "DATABASE_URL" and isinstance(v, str):
                # Redact password in connection string: postgresql://user:pass@host/db -> postgresql://user:[REDACTED]@host/db
                if "@" in v and ":" in v.split("@")[0]:
                    parts = v.split("@", 1)
                    prefix = parts[0]
                    scheme_and_user = prefix.rsplit(":", 1)[0]
                    safe[k] = f"{scheme_and_user}:[REDACTED]@{parts[1]}"
                else:
                    safe[k] = v
            elif k in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND") and isinstance(v, str):
                if "@" in v and ":" in v.split("@")[0]:
                    parts = v.split("@", 1)
                    safe[k] = f"{parts[0].split('://')[0]}://[REDACTED]@{parts[1]}"
                else:
                    safe[k] = v
            else:
                safe[k] = v
        return safe


settings = Settings()

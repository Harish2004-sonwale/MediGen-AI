from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MediGen AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"

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


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

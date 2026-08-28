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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

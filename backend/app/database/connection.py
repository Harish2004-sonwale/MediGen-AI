from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Determine dialect-specific connection arguments
connect_args = {}
if settings.DATABASE_URL.startswith("postgresql"):
    connect_args["connect_timeout"] = settings.DB_CONNECT_TIMEOUT

# Configure SQLAlchemy 2.0 Engine
# pool_pre_ping=True verifies connection liveness before returning it from the pool
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    echo=False,
)

# Configure SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

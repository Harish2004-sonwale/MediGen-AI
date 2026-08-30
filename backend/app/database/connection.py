from typing import Any, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Determine dialect-specific connection arguments
connect_args = {}
engine_kwargs: Dict[str, Any] = {
    "pool_pre_ping": True,
    "echo": False,
}

if settings.DATABASE_URL.startswith("postgresql"):
    connect_args["connect_timeout"] = getattr(settings, "DB_CONNECT_TIMEOUT", 10)
    connect_args["options"] = f"-c statement_timeout={getattr(settings, 'DB_STATEMENT_TIMEOUT_MS', 30000)} -c lock_timeout={getattr(settings, 'DB_LOCK_TIMEOUT_MS', 10000)}"
    engine_kwargs.update({
        "pool_size": getattr(settings, "DB_POOL_SIZE", 20),
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 10),
        "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30),
        "pool_recycle": getattr(settings, "DB_POOL_RECYCLE_SECONDS", 1800),
    })
elif "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

# Configure SQLAlchemy 2.0 Engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

# Configure SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def check_db_connectivity() -> bool:
    """Execute lightweight SELECT 1 to verify proactive database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def get_connection_pool_status() -> Dict[str, Any]:
    """Inspect current SQLAlchemy connection pool telemetry."""
    pool = getattr(engine, "pool", None)
    if not pool or isinstance(pool, NullPool):
        return {"type": "NullPool", "size": 0, "checked_in": 0, "checked_out": 0, "overflow": 0}

    return {
        "type": type(pool).__name__,
        "size": getattr(pool, "size", lambda: 0)(),
        "checked_in": getattr(pool, "checkedin", lambda: 0)(),
        "checked_out": getattr(pool, "checkedout", lambda: 0)(),
        "overflow": getattr(pool, "overflow", lambda: 0)(),
    }

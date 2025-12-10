from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Lazy initialization for engine and session
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine (lazy initialization).

    This delays connection until first actual use, allowing the app
    to start even if database config is resolved at runtime (e.g., OAuth).
    """
    global _engine
    if _engine is None:
        from app.core.config import settings
        _engine = create_engine(
            settings.effective_database_url,
            poolclass=NullPool,
            connect_args={
                "connect_timeout": 10,
            },
            pool_pre_ping=True,
        )
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Session:
    """Dependency for FastAPI endpoints."""
    session_factory = get_session_local()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
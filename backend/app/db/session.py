"""
Database session management with support for OAuth token authentication.

When running in Databricks Apps with OAuth, tokens are automatically refreshed
before creating new connections.
"""
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# Lazy initialization for engine and session
_engine = None
_SessionLocal = None
_using_oauth = False


def _get_oauth_database_url() -> str:
    """Get database URL using OAuth token (refreshed if needed)"""
    from app.db.lakebase_oauth import get_lakebase_oauth_manager

    oauth_mgr = get_lakebase_oauth_manager()
    if oauth_mgr:
        return oauth_mgr.get_database_url()
    return None


def get_engine():
    """Get or create the database engine (lazy initialization).

    This delays connection until first actual use, allowing the app
    to start even if database config is resolved at runtime (e.g., OAuth).

    For OAuth mode, we use NullPool so each request gets a fresh connection
    with a fresh token.
    """
    global _engine, _using_oauth

    if _engine is None:
        from app.core.config import settings
        from app.db.lakebase_oauth import get_lakebase_oauth_manager

        # Check if OAuth is available
        oauth_mgr = get_lakebase_oauth_manager()

        if oauth_mgr and oauth_mgr.is_oauth_available:
            # OAuth mode - use a creator function that gets fresh tokens
            logger.info("Database engine: Using OAuth token authentication")
            _using_oauth = True

            # Get schema from environment
            import os
            schema = os.environ.get('LAKEBASE_SCHEMA', 'metadata_manager')
            logger.info(f"Database engine: Using schema '{schema}'")

            # Get initial URL to create engine (token will be refreshed on connect)
            database_url = oauth_mgr.get_database_url(schema=schema)

            _engine = create_engine(
                database_url,
                poolclass=NullPool,  # No pooling - each connection gets fresh token
                connect_args={
                    "connect_timeout": 10,
                },
            )

            # Add event listener to refresh credentials before connect
            @event.listens_for(_engine, "do_connect")
            def provide_token_on_connect(dialect, conn_rec, cargs, cparams):
                """Refresh OAuth token before each connection"""
                # Get fresh credentials
                fresh_mgr = get_lakebase_oauth_manager()
                if fresh_mgr:
                    params = fresh_mgr.get_connection_params()
                    cparams['user'] = params['user']
                    cparams['password'] = params['password']
                    logger.debug(f"OAuth: Refreshed credentials (token expires in {fresh_mgr.token_expires_in}s)")

        else:
            # Static credentials mode
            logger.info("Database engine: Using static credentials from DATABASE_URL")
            _using_oauth = False

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


def is_using_oauth() -> bool:
    """Check if the database is using OAuth authentication"""
    # Trigger engine initialization if needed
    get_engine()
    return _using_oauth

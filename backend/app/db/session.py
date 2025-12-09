from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.core.config import settings


# Use NullPool for serverless compatibility (Lakebase and Neon)
# This ensures connections are not pooled and properly released
engine = create_engine(
    settings.effective_database_url,
    poolclass=NullPool,
    connect_args={
        "connect_timeout": 10,
    },
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
database/schema/connection.py

Provides the SQLAlchemy engine and session factory.
Used by the loaders and pipeline. The backend (Member 2)
should import get_session() from here for its own DB access.

Configuration is read from environment variables so Docker /
production deployments just set DATABASE_URL.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from .models import Base

# ─── Load .env for local development ──────────────────────────
# python-dotenv is used only if available. In production (Docker/CI)
# environment variables are injected directly and no .env file is needed.
# We search upward from this file to find the project-root .env.
try:
    from dotenv import load_dotenv as _load_dotenv

    _here = Path(__file__).resolve()
    # Walk up until we find a .env file or run out of parents
    for _parent in [_here.parent, _here.parent.parent, _here.parent.parent.parent,
                    _here.parent.parent.parent.parent]:
        _env_file = _parent / ".env"
        if _env_file.exists():
            _load_dotenv(_env_file, override=False)  # override=False: real env vars win
            break
except ImportError:
    pass  # python-dotenv not installed — rely on environment variables directly

# ─── Database URL ─────────────────────────────────────────────
# Priority: DATABASE_URL env var → individual DB_* vars

def _build_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5432")
    name     = os.getenv("DB_NAME", "customer_data_platform")
    user     = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # detect stale connections
    pool_size=5,
    max_overflow=10,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Return a new SQLAlchemy session. Caller must close it."""
    return SessionLocal()


def init_db() -> None:
    """
    Create all tables if they don't exist.
    In production you'd use Alembic migrations instead;
    this is the quick-start path for dev/testing.
    """
    Base.metadata.create_all(bind=engine)


def check_connection() -> bool:
    """Ping the database. Returns True if reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

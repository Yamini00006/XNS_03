"""
backend/common/db.py

Shared helpers for talking to the Member-3-owned tables
(upload_files, processing_jobs, customers, customer_sources,
validation_errors, data_quality, processing_logs).

These tables are defined with SQLAlchemy in database/schema/models.py
and database/schema/schema.sql — Member 2 does NOT redefine them as
Django models. Instead every view in apps/files, apps/processing,
apps/data, apps/dashboard, apps/exports, apps/chatbot opens a
SQLAlchemy session via session_scope() below and works with the
existing SQLAlchemy model classes directly.
"""

from __future__ import annotations

import enum
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from sqlalchemy.orm import Session

from database.schema.connection import get_session


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Provide a transactional SQLAlchemy session.

    Commits on success, rolls back on exception, always closes.
    Usage:
        with session_scope() as session:
            session.add(obj)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def to_dict(obj: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """
    Convert a SQLAlchemy declarative model instance into a plain,
    JSON-serializable dict (datetimes -> isoformat, enums -> .value).
    Relationship attributes are not included (avoids lazy-load errors
    once the session is closed) unless explicitly selected by the caller.
    """
    exclude = exclude or set()
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        name = column.name
        if name in exclude:
            continue
        value = getattr(obj, name)
        result[name] = _serialize_value(value)
    return result


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value
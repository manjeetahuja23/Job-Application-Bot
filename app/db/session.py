"""Database session management."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()
_engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)


def get_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""

    return _engine


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager wrapper around a database session."""

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - safeguard rollback path
        session.rollback()
        raise
    finally:
        session.close()

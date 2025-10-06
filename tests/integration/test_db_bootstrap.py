"""Integration tests for database bootstrap."""
from __future__ import annotations

import importlib

import pytest

pytest.importorskip("alembic")

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core import settings as settings_module


def test_migrations_create_expected_tables(tmp_path, monkeypatch) -> None:
    """Running migrations should create the core tables."""

    db_path = tmp_path / "autojob.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    settings_module._get_settings.cache_clear()

    session_module = importlib.import_module("app.db.session")
    importlib.reload(session_module)

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = session_module.get_engine()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {"jobs", "profiles", "matches", "documents"}.issubset(tables)

    # ensure indexes applied
    job_indexes = {index["name"] for index in inspector.get_indexes("jobs")}
    match_indexes = {index["name"] for index in inspector.get_indexes("matches")}

    assert "ix_jobs_posted_at" in job_indexes
    assert "ix_matches_score" in match_indexes

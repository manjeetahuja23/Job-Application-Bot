"""Integration test for the Greenhouse ingestion pipeline."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest

pytest.importorskip("httpx")

import httpx
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core import settings as settings_module
from app.db import models
from app.ingestion.greenhouse import GreenhouseIngestion

pytest.importorskip("alembic")


class StubHttpClient:
    """Minimal HTTP client that returns fixture responses with ETag support."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        if headers and headers.get("If-None-Match") == "test-etag":
            return httpx.Response(304, headers={"ETag": "test-etag"})
        return httpx.Response(200, json=self.payload, headers={"ETag": "test-etag"})


def _setup_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    db_path = tmp_path / "autojob.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    settings_module._get_settings.cache_clear()
    session_module = importlib.import_module("app.db.session")
    importlib.reload(session_module)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    return session_module


def test_greenhouse_ingestion_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Greenhouse ingestion should upsert jobs and skip when unchanged."""

    session_module = _setup_database(tmp_path, monkeypatch)

    fixture_path = Path("tests/fixtures/greenhouse_jobs.json")
    payload = json.loads(fixture_path.read_text())

    ingestion = GreenhouseIngestion(
        board_url="https://boards.greenhouse.io/example", client=StubHttpClient(payload)
    )

    with session_module.session_scope() as session:
        result = ingestion.ingest(session)
        assert result.inserted == 2
        rows = session.execute(select(models.Job)).scalars().all()
        assert len(rows) == 2
        for row in rows:
            assert row.description_text
            assert row.location

    with session_module.session_scope() as session:
        result_again = ingestion.ingest(session)
        assert result_again.fetched == 0
        assert result_again.inserted == 0
        assert result_again.updated == 0

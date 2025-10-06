"""End-to-end tests for document tailoring."""
from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
pytest.importorskip("alembic")

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core import settings as settings_module
from app.db import models
from app.docs import tailor


def _setup_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    db_path = tmp_path / "autojob_tailor.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    settings_module._get_settings.cache_clear()
    session_module = importlib.import_module("app.db.session")
    importlib.reload(session_module)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    return session_module


def test_tailor_flow_creates_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tailoring should persist markdown and text files and store metadata."""

    session_module = _setup_database(tmp_path, monkeypatch)
    storage_root = tmp_path / "storage"

    with session_module.session_scope() as session:
        profile = models.Profile(
            name="Test Profile",
            skills="WordPress, PHP, JavaScript",
            keywords="wordpress,php,javascript",
            geo_preference="Remote",
            salary_min=None,
            salary_max=None,
            resume_template_path="app/docs/templates/resume_base.md",
            cover_template_path="app/docs/templates/cover_base.md",
        )
        session.add(profile)

        job = models.Job(
            id=uuid4(),
            source="greenhouse",
            external_id="123",
            url="https://example.com/job",
            company="Example Co",
            title="WordPress Engineer",
            location="Remote",
            remote=True,
            posted_at=None,
            description_html="<p>Build WordPress and WooCommerce experiences with PHP and JavaScript.</p>",
            description_text="Build WordPress and WooCommerce experiences with PHP and JavaScript.",
            tags="wordpress,php,woocommerce",
            salary_min=None,
            salary_max=None,
            raw_json={"id": "123"},
        )
        session.add(job)
        session.flush()
        job_id = job.id
        profile_id = profile.id

    with session_module.session_scope() as session:
        job = session.get(models.Job, job_id)
        profile = session.get(models.Profile, profile_id)
        result = tailor.tailor_job_documents(session, job, profile, storage_root=storage_root)
        session.commit()

    resume_text = Path(result.resume_path).read_text(encoding="utf-8")
    cover_text = Path(result.cover_path).read_text(encoding="utf-8")

    assert "Example Co" in resume_text
    assert "WordPress Engineer" in resume_text
    assert "Example Co" in cover_text
    assert any(keyword in resume_text for keyword in ("WordPress", "WooCommerce", "PHP"))
    assert result.resume_path.with_suffix(".txt").exists()
    assert result.cover_path.with_suffix(".txt").exists()

    with session_module.session_scope() as session:
        stored = session.execute(
            select(models.Document).where(
                models.Document.job_id == job_id,
                models.Document.profile_id == profile_id,
            )
        ).scalar_one()
        assert stored.resume_path == str(result.resume_path)
        assert stored.cover_path == str(result.cover_path)

    # ensure keywords surfaced for API consumers
    assert any("WordPress" in keyword for keyword in result.keywords)

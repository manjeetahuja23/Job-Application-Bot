"""Integration tests for the job listing API."""
from __future__ import annotations

import importlib
from uuid import uuid4

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from app.core import settings as settings_module


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Provide a FastAPI test client backed by a temporary SQLite database."""

    db_path = tmp_path / "autojob_api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CELERY_EAGER", "true")

    settings_module._get_settings.cache_clear()
    session_module = importlib.import_module("app.db.session")
    importlib.reload(session_module)

    models_module = importlib.import_module("app.db.models")
    models_module.Base.metadata.create_all(session_module.get_engine())

    with session_module.session_scope() as session:
        profile = models_module.Profile(
            name="Test Profile",
            skills="Python, API, Automation",
            keywords="python,api,automation",
            geo_preference="Remote",
            salary_min=90000,
            salary_max=140000,
            resume_template_path="app/docs/templates/resume_base.md",
            cover_template_path="app/docs/templates/cover_base.md",
        )
        session.add(profile)
        session.flush()

        job = models_module.Job(
            id=uuid4(),
            source="greenhouse",
            external_id="123",
            url="https://example.com/jobs/123",
            company="Example Co",
            title="Automation Engineer",
            location="Remote",
            remote=True,
            posted_at=None,
            description_html="<p>Automate the world with Python.</p>",
            description_text="Automate the world with Python and APIs.",
            tags="python,api",
            raw_json={"id": "123"},
        )
        session.add(job)
        session.flush()
        session.add(
            models_module.Match(
                job_id=job.id,
                profile_id=profile.id,
                score=0.82,
                reason="Matched keywords: python, api",
            )
        )

    main_module = importlib.import_module("app.api.main")
    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_job_search_filters(api_client: TestClient) -> None:
    """The job search endpoint should respect filters and return data."""

    response = api_client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Automation Engineer"
    assert data[0]["score"] == pytest.approx(0.82, rel=1e-3)

    filtered = api_client.get("/jobs", params={"min_score": 0.9})
    assert filtered.status_code == 200
    assert filtered.json() == []

    detail = api_client.get(f"/jobs/{data[0]['id']}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["company"] == "Example Co"
    assert "Automate" in detail_payload["description_text"]

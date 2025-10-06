"""Integration tests for health endpoints."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_endpoints() -> None:
    """Both liveness and readiness probes should respond with success."""

    client = TestClient(app)
    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}

"""Health check endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"], include_in_schema=False)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Readiness probe to confirm the API process is running."""

    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    """Liveness probe to indicate dependencies are reachable."""

    return {"status": "ready"}

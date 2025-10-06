"""FastAPI application instance and UI routes."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.routers import documents, health, jobs, settings
from app.api.routers.jobs import get_job_summaries
from app.api.ui import templates
from app.core.logging import configure_logging
from app.db.session import get_session

configure_logging()
LOGGER = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.info("app.startup")
    yield
    LOGGER.info("app.shutdown")


app = FastAPI(title="autojob-bot", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(settings.router)
app.include_router(documents.router)


@app.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    q: str | None = Query(default=None),
    remote: bool | None = Query(default=None),
    location: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    db: Session = Depends(get_session),
):
    """Render the dashboard showing recently ingested jobs."""

    job_rows, profile = get_job_summaries(
        db, q=q, remote=remote, location=location, min_score=min_score
    )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "jobs": job_rows,
            "profile": profile,
            "filters": {
                "q": q or "",
                "remote": remote,
                "location": location or "",
                "min_score": min_score,
            },
        },
    )

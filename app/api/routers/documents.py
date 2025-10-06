"""Document generation endpoints."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.api.ui import templates
from app.db import models
from app.db.session import get_session
from app.docs import exports, tailor

router = APIRouter()


@router.post("/jobs/{job_id}/tailor")
def tailor_documents(
    job_id: uuid.UUID,
    profile_id: int,
    request: Request,
    db: Session = Depends(get_session),
) -> dict[str, object] | Response:
    """Tailor documents for a given job/profile pair."""

    job = db.get(models.Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.get(models.Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    result = tailor.tailor_job_documents(db, job, profile)
    db.commit()
    db.refresh(result.document)

    payload = {
        "document_id": result.document.id,
        "resume_path": str(result.resume_path),
        "cover_path": str(result.cover_path),
        "keywords": result.keywords,
        "achievements": result.achievements,
    }

    if request.headers.get("hx-request") == "true" or "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            "tailor_result.html",
            {
                "request": request,
                "document": payload,
                "job": job,
            },
        )

    return payload


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    *,
    fmt: str = Query("md", pattern="^(md|txt)$"),
    kind: str = Query("resume", pattern="^(resume|cover)$"),
    db: Session = Depends(get_session),
) -> FileResponse:
    """Stream a tailored document in Markdown or plain text form."""

    document = db.get(models.Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    base_path = Path(document.resume_path if kind == "resume" else document.cover_path)
    if fmt == "txt":
        candidate = base_path.with_suffix(".txt")
    else:
        candidate = base_path

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Requested document file is unavailable.")

    media_type = "text/markdown" if fmt == "md" else "text/plain"
    return FileResponse(candidate, media_type=media_type, filename=candidate.name)

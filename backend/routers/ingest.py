"""Routes for ingesting new classes."""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from schemas import IngestRequest, IngestResponse, IngestStatus
from services.ingest_service import jobs, start_ingest

router = APIRouter()


@router.post("", response_model=IngestResponse)
def create_ingest_job(request: IngestRequest):
    """Start a new ingest job in the background."""
    job_id = str(uuid4())
    class_id = str(uuid4())[:8]
    start_ingest(job_id, request.url, request.title, class_id, request.materia_id)
    return IngestResponse(job_id=job_id)


@router.get("/{job_id}", response_model=IngestStatus)
def get_ingest_status(job_id: str):
    """Get the status of an ingest job."""
    status = jobs.get(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return status

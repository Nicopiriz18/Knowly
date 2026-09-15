"""Routes for ingesting new classes."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from config import settings
from deps import CurrentUser, get_current_user
from schemas import IngestRequest, IngestResponse, IngestStatus
from services.ingest_service import job_owners, jobs, start_ingest
from services.materia_service import get_materia
from services.rate_limit import check_rate_limit

router = APIRouter()


@router.post("", response_model=IngestResponse)
def create_ingest_job(request: IngestRequest, user: CurrentUser = Depends(get_current_user)):
    """Start a new ingest job in the background."""
    if get_materia(request.materia_id, user.email) is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    check_rate_limit(f"ingest:{user.email}", settings.ingest_limit_per_day, 86400)

    job_id = str(uuid4())
    class_id = str(uuid4())[:8]
    start_ingest(job_id, request.url, request.title, class_id, request.materia_id, user.email)
    return IngestResponse(job_id=job_id)


@router.get("/{job_id}", response_model=IngestStatus)
def get_ingest_status(job_id: str, user: CurrentUser = Depends(get_current_user)):
    """Get the status of an ingest job."""
    status = jobs.get(job_id)
    if status is None or job_owners.get(job_id) != user.email:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return status

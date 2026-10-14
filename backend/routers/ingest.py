"""Routes for ingesting new classes."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from config import settings
from deps import CurrentUser, get_current_user
from schemas import IngestRequest, IngestResponse, IngestStatus
from services.class_service import list_classes
from services.ingest_service import active_job_count, job_owners, jobs, queue_position, start_ingest
from services.materia_service import get_materia
from services.rate_limit import check_rate_limit

router = APIRouter()


def _check_quota(user: CurrentUser) -> None:
    """Per-user limits that keep ingest costs bounded. Admins are exempt."""
    if user.is_admin:
        return
    active = active_job_count(user.email)
    if active >= settings.max_active_ingests_per_user:
        raise HTTPException(
            status_code=429,
            detail="Ya tenés un video procesándose. Esperá a que termine para agregar otro.",
        )
    if len(list_classes(user.email)) + active >= settings.max_classes_per_user:
        raise HTTPException(
            status_code=403,
            detail=f"Llegaste al límite de {settings.max_classes_per_user} clases. Borrá alguna para agregar otra.",
        )
    check_rate_limit(f"ingest:{user.email}", settings.ingest_limit_per_day, 86400)


@router.post("", response_model=IngestResponse)
def create_ingest_job(request: IngestRequest, user: CurrentUser = Depends(get_current_user)):
    """Queue a new ingest job."""
    if get_materia(request.materia_id, user.email) is None:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    _check_quota(user)

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
    position = queue_position(job_id) if status.status == "pending" else None
    if position is not None:
        ahead = position - 1
        message = (
            "Sos el próximo en la cola..."
            if ahead == 0
            else f"En cola: {ahead} video{'s' if ahead > 1 else ''} antes que el tuyo..."
        )
        return status.model_copy(update={"message": message})
    return status

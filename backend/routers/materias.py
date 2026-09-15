"""Routes for managing materias (subjects)."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from config import settings
from deps import CurrentUser, get_current_user
from schemas import CreateMateriaRequest, MateriaInfo
from services.materia_service import (
    list_materias,
    create_materia,
    delete_materia,
)
from services.class_service import count_classes_by_materia, delete_classes_by_materia
from services.pinecone_client import get_index

router = APIRouter()


@router.get("", response_model=list[MateriaInfo])
def list_all_materias(user: CurrentUser = Depends(get_current_user)):
    """List the user's materias with their class counts."""
    materias = list_materias(user.email)
    return [
        MateriaInfo(
            materia_id=m["materia_id"],
            title=m["title"],
            class_count=count_classes_by_materia(m["materia_id"]),
        )
        for m in materias
    ]


@router.post("", response_model=MateriaInfo)
def create_new_materia(request: CreateMateriaRequest, user: CurrentUser = Depends(get_current_user)):
    """Create a new materia with an auto-generated ID."""
    materia_id = str(uuid4())[:8]
    result = create_materia(materia_id, request.title, user.email)
    return MateriaInfo(materia_id=result["materia_id"], title=result["title"], class_count=0)


@router.delete("/{materia_id}")
def delete_existing_materia(materia_id: str, user: CurrentUser = Depends(get_current_user)):
    """Delete a materia and all its classes."""
    if not delete_materia(materia_id, user.email):
        raise HTTPException(status_code=404, detail=f"Materia '{materia_id}' not found.")

    # Delete vectors from Pinecone
    index = get_index()
    index.delete(filter={"materia_id": {"$eq": materia_id}})

    # Remove classes from registry and get their IDs for disk cleanup
    class_ids = delete_classes_by_materia(materia_id)

    # Remove audio, transcript, and visual files from disk
    data_dir = Path(settings.data_dir)
    for cid in class_ids:
        for subdir in ("audio", "transcripts", "visual"):
            for f in (data_dir / subdir).glob(f"{cid}.*"):
                f.unlink(missing_ok=True)

    return {"detail": f"Materia '{materia_id}' and all its classes deleted."}

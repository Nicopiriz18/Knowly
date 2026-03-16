"""Routes for managing materias (subjects)."""

from pathlib import Path
from uuid import uuid4

import chromadb
from fastapi import APIRouter, HTTPException

from config import settings
from schemas import CreateMateriaRequest, MateriaInfo
from services.materia_service import (
    list_materias,
    get_materia,
    create_materia,
    delete_materia,
)

router = APIRouter()


@router.get("", response_model=list[MateriaInfo])
def list_all_materias():
    """List all materias with their class counts."""
    materias = list_materias()

    # Count unique classes per materia from ChromaDB
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    class_counts: dict[str, set[str]] = {}
    if collection.count() > 0:
        all_data = collection.get(include=["metadatas"])
        for meta in all_data["metadatas"]:
            mid = meta.get("materia_id", "")
            cid = meta["class_id"]
            class_counts.setdefault(mid, set()).add(cid)

    return [
        MateriaInfo(
            materia_id=m["materia_id"],
            title=m["title"],
            class_count=len(class_counts.get(m["materia_id"], set())),
        )
        for m in materias
    ]


@router.post("", response_model=MateriaInfo)
def create_new_materia(request: CreateMateriaRequest):
    """Create a new materia with an auto-generated ID."""
    materia_id = str(uuid4())[:8]
    result = create_materia(materia_id, request.title)
    return MateriaInfo(materia_id=result["materia_id"], title=result["title"], class_count=0)


@router.delete("/{materia_id}")
def delete_existing_materia(materia_id: str):
    """Delete a materia and all its classes."""
    if not delete_materia(materia_id):
        raise HTTPException(status_code=404, detail=f"Materia '{materia_id}' not found.")

    # Also delete all chunks belonging to this materia
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    class_ids: set[str] = set()
    if collection.count() > 0:
        results = collection.get(
            where={"materia_id": materia_id},
            include=["metadatas"],
        )
        if results["ids"]:
            for meta in results["metadatas"]:
                class_ids.add(meta["class_id"])
            collection.delete(ids=results["ids"])

    # Remove audio and transcript files from disk
    data_dir = Path(settings.data_dir)
    for cid in class_ids:
        for subdir in ("audio", "transcripts", "visual"):
            for f in (data_dir / subdir).glob(f"{cid}.*"):
                f.unlink(missing_ok=True)

    return {"detail": f"Materia '{materia_id}' and all its classes deleted."}

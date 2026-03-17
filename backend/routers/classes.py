"""Routes for managing indexed classes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import settings
from schemas import ClassInfo
from services.class_service import list_classes as get_all_classes, delete_class as remove_class_registry
from services.pinecone_client import get_index

router = APIRouter()


@router.get("", response_model=list[ClassInfo])
def list_classes(materia_id: str | None = None):
    """List all indexed classes with their chunk counts, optionally filtered by materia."""
    classes = get_all_classes(materia_id)
    return [
        ClassInfo(
            class_id=c["class_id"],
            class_title=c["class_title"],
            source_url=c["source_url"],
            chunk_count=c.get("chunk_count", 0),
            materia_id=c.get("materia_id", ""),
        )
        for c in classes
    ]


@router.delete("/{class_id}")
def delete_class(class_id: str):
    """Delete all chunks for a given class_id."""
    if not remove_class_registry(class_id):
        raise HTTPException(status_code=404, detail=f"Class '{class_id}' not found.")

    # Delete vectors from Pinecone
    index = get_index()
    index.delete(filter={"class_id": {"$eq": class_id}})

    # Remove audio, transcript, and visual files from disk
    data_dir = Path(settings.data_dir)
    for subdir in ("audio", "transcripts", "visual"):
        for f in (data_dir / subdir).glob(f"{class_id}.*"):
            f.unlink(missing_ok=True)

    return {"detail": f"Deleted class '{class_id}' and its vectors."}

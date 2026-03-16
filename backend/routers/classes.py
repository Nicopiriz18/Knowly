"""Routes for managing indexed classes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
import chromadb

from config import settings
from schemas import ClassInfo

router = APIRouter()


@router.get("", response_model=list[ClassInfo])
def list_classes(materia_id: str | None = None):
    """List all indexed classes with their chunk counts, optionally filtered by materia."""
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    if collection.count() == 0:
        return []

    get_params: dict = {"include": ["metadatas"]}
    if materia_id is not None:
        get_params["where"] = {"materia_id": materia_id}

    all_data = collection.get(**get_params)
    metadatas = all_data["metadatas"]

    # Aggregate unique classes
    classes: dict[str, ClassInfo] = {}
    for meta in metadatas:
        cid = meta["class_id"]
        if cid not in classes:
            classes[cid] = ClassInfo(
                class_id=cid,
                class_title=meta["class_title"],
                source_url=meta["source_url"],
                chunk_count=1,
                materia_id=meta.get("materia_id", ""),
            )
        else:
            classes[cid].chunk_count += 1

    return list(classes.values())


@router.delete("/{class_id}")
def delete_class(class_id: str):
    """Delete all chunks for a given class_id."""
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    # Get all chunk IDs for this class
    results = collection.get(
        where={"class_id": class_id},
        include=[],
    )

    if not results["ids"]:
        raise HTTPException(status_code=404, detail=f"Class '{class_id}' not found.")

    collection.delete(ids=results["ids"])

    # Remove audio and transcript files from disk
    data_dir = Path(settings.data_dir)
    for subdir in ("audio", "transcripts", "visual"):
        for f in (data_dir / subdir).glob(f"{class_id}.*"):
            f.unlink(missing_ok=True)

    return {"detail": f"Deleted {len(results['ids'])} chunks for class '{class_id}'."}

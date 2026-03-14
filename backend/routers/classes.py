"""Routes for managing indexed classes."""

from fastapi import APIRouter, HTTPException
import chromadb

from config import settings
from schemas import ClassInfo

router = APIRouter()


@router.get("", response_model=list[ClassInfo])
def list_classes():
    """List all indexed classes with their chunk counts."""
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    if collection.count() == 0:
        return []

    # Get all documents metadata
    all_data = collection.get(include=["metadatas"])
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

    return {"detail": f"Deleted {len(results['ids'])} chunks for class '{class_id}'."}

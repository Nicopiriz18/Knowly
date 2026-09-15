"""JSON-backed registry of classes (same pattern as materia_service.py)."""

import json
from pathlib import Path

from config import settings
from services.materia_service import legacy_owner

_CLASSES_FILE = Path(settings.data_dir) / "classes_registry.json"


def _load() -> dict[str, dict]:
    """Load classes from disk. Returns {class_id: {class_title, source_url, materia_id, chunk_count, owner}}."""
    if not _CLASSES_FILE.exists():
        return {}
    with open(_CLASSES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, dict]) -> None:
    _CLASSES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_CLASSES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _owner(info: dict) -> str:
    return info.get("owner") or legacy_owner()


def list_classes(owner: str, materia_id: str | None = None) -> list[dict]:
    """List the owner's classes, optionally filtered by materia_id."""
    results = []
    for cid, info in _load().items():
        if _owner(info) != owner:
            continue
        if materia_id is not None and info.get("materia_id") != materia_id:
            continue
        results.append({"class_id": cid, **info})
    return results


def get_class(class_id: str, owner: str) -> dict | None:
    """Return the class only if it belongs to `owner`."""
    info = _load().get(class_id)
    if info is None or _owner(info) != owner:
        return None
    return {"class_id": class_id, **info}


def register_class(
    class_id: str,
    class_title: str,
    source_url: str,
    materia_id: str,
    chunk_count: int,
    owner: str,
) -> None:
    """Register or update a class in the registry."""
    data = _load()
    data[class_id] = {
        "class_title": class_title,
        "source_url": source_url,
        "materia_id": materia_id,
        "chunk_count": chunk_count,
        "owner": owner,
    }
    _save(data)


def delete_class(class_id: str, owner: str) -> bool:
    """Remove a class from the registry. Returns True if it existed and belonged to owner."""
    data = _load()
    if class_id not in data or _owner(data[class_id]) != owner:
        return False
    del data[class_id]
    _save(data)
    return True


def delete_classes_by_materia(materia_id: str) -> list[str]:
    """Remove all classes for a materia. Returns the deleted class_ids."""
    data = _load()
    to_delete = [cid for cid, info in data.items() if info.get("materia_id") == materia_id]
    for cid in to_delete:
        del data[cid]
    _save(data)
    return to_delete


def count_classes_by_materia(materia_id: str) -> int:
    """Count unique classes for a materia."""
    data = _load()
    return sum(1 for info in data.values() if info.get("materia_id") == materia_id)

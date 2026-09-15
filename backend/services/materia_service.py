"""Simple JSON-backed storage for materias."""

import json
from pathlib import Path

from config import settings

_MATERIAS_FILE = Path(settings.data_dir) / "materias.json"


def legacy_owner() -> str:
    """Owner assigned to records created before per-user data existed."""
    return settings.admin_emails[0] if settings.admin_emails else ""


def _load() -> dict[str, dict]:
    """Load materias from disk. Returns {materia_id: {title: str, owner: str}}."""
    if not _MATERIAS_FILE.exists():
        return {}
    with open(_MATERIAS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, dict]) -> None:
    _MATERIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_MATERIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _owner(info: dict) -> str:
    return info.get("owner") or legacy_owner()


def list_materias(owner: str) -> list[dict]:
    return [
        {"materia_id": mid, "title": info["title"]}
        for mid, info in _load().items()
        if _owner(info) == owner
    ]


def get_materia(materia_id: str, owner: str) -> dict | None:
    """Return the materia only if it belongs to `owner`."""
    info = _load().get(materia_id)
    if info is None or _owner(info) != owner:
        return None
    return {"materia_id": materia_id, "title": info["title"]}


def create_materia(materia_id: str, title: str, owner: str) -> dict:
    data = _load()
    data[materia_id] = {"title": title, "owner": owner}
    _save(data)
    return {"materia_id": materia_id, "title": title}


def delete_materia(materia_id: str, owner: str) -> bool:
    data = _load()
    if materia_id not in data or _owner(data[materia_id]) != owner:
        return False
    del data[materia_id]
    _save(data)
    return True

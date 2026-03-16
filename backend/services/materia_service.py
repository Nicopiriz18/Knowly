"""Simple JSON-backed storage for materias."""

import json
from pathlib import Path

from config import settings

_MATERIAS_FILE = Path(settings.data_dir) / "materias.json"


def _load() -> dict[str, dict]:
    """Load materias from disk. Returns {materia_id: {title: str}}."""
    if not _MATERIAS_FILE.exists():
        return {}
    with open(_MATERIAS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, dict]) -> None:
    _MATERIAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_MATERIAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_materias() -> list[dict]:
    return [
        {"materia_id": mid, "title": info["title"]}
        for mid, info in _load().items()
    ]


def get_materia(materia_id: str) -> dict | None:
    data = _load()
    info = data.get(materia_id)
    if info is None:
        return None
    return {"materia_id": materia_id, "title": info["title"]}


def create_materia(materia_id: str, title: str) -> dict:
    data = _load()
    data[materia_id] = {"title": title}
    _save(data)
    return {"materia_id": materia_id, "title": title}


def delete_materia(materia_id: str) -> bool:
    data = _load()
    if materia_id not in data:
        return False
    del data[materia_id]
    _save(data)
    return True

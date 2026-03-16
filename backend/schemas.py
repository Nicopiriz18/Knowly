from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------

class CreateMateriaRequest(BaseModel):
    title: str


class MateriaInfo(BaseModel):
    materia_id: str
    title: str
    class_count: int = 0


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class ClassInfo(BaseModel):
    class_id: str
    class_title: str
    source_url: str
    chunk_count: int
    materia_id: str


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    url: str
    title: str
    materia_id: str


class IngestResponse(BaseModel):
    job_id: str


class IngestStatus(BaseModel):
    status: Literal["pending", "downloading", "transcribing", "embedding", "done", "error"]
    message: str = ""
    progress: int = 0


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str
    class_id: str | None = None
    materia_id: str | None = None


class Source(BaseModel):
    class_title: str
    start_time: int
    end_time: int
    timestamp_link: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth & admin
# ---------------------------------------------------------------------------

class LoginStartRequest(BaseModel):
    email: EmailStr


class LoginStartResponse(BaseModel):
    status: Literal["otp_sent", "pending"]


class LoginVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginVerifyResponse(BaseModel):
    token: str


class MeResponse(BaseModel):
    email: str
    is_admin: bool


class UserInfo(BaseModel):
    email: str
    status: Literal["pending", "approved", "rejected"]
    created_at: float
    decided_at: float | None = None
    is_admin: bool = False


class UpdateUserStatusRequest(BaseModel):
    status: Literal["approved", "rejected"]


# ---------------------------------------------------------------------------
# Materias
# ---------------------------------------------------------------------------

class CreateMateriaRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


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

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class IngestRequest(BaseModel):
    url: str
    title: str = Field(min_length=1, max_length=200)
    materia_id: str

    @field_validator("url")
    @classmethod
    def _youtube_only(cls, v: str) -> str:
        v = v.strip()
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or (parsed.hostname or "").lower() not in _YOUTUBE_HOSTS:
            raise ValueError("La URL debe ser un video de YouTube.")
        return v


class IngestResponse(BaseModel):
    job_id: str


class IngestStatus(BaseModel):
    status: Literal["pending", "downloading", "transcribing", "extracting_frames", "analyzing_frames", "embedding", "done", "error"]
    message: str = ""
    progress: int = 0


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
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

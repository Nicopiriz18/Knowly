import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

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
    # None = no limit (admins)
    max_classes: int | None
    max_video_minutes: int


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


class ClassRenameRequest(BaseModel):
    class_title: str = Field(min_length=1, max_length=200)

    @field_validator("class_title", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_EXAMPLE = "https://www.youtube.com/watch?v=..."


def youtube_url_error(raw: str) -> str | None:
    """Explain why `raw` is not a usable YouTube video link, or None if it is.

    Distinguishes "not a link at all", "another site", "a YouTube page that isn't
    a video" (channel, playlist, search) and "a truncated video ID", so the user
    knows what to fix instead of getting a generic rejection.
    """
    if not raw:
        return f"Pegá el link del video. Por ejemplo: {_YOUTUBE_EXAMPLE}"
    if " " in raw or "\n" in raw:
        return "El link tiene espacios o saltos de línea. Pegá solo la URL del video."

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower()
    if not host or "." not in host:
        return f"Eso no parece un link. Pegá la URL completa del video, por ejemplo: {_YOUTUBE_EXAMPLE}"
    if parsed.scheme not in ("http", "https"):
        return "El link tiene que empezar con http:// o https://."
    if host not in _YOUTUBE_HOSTS:
        return f"Por ahora solo se aceptan videos de YouTube, y el link que pegaste es de {host}."

    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)
    video_id: str | None = None
    if host == "youtu.be":
        video_id = path.lstrip("/").split("/")[0] or None
    elif path == "/watch":
        video_id = (query.get("v") or [None])[0]
    elif path.startswith(("/shorts/", "/live/", "/embed/", "/v/")):
        video_id = path.split("/")[2] if path.count("/") >= 2 else None
    elif path == "/playlist" or (not path and "list" in query):
        return "Ese link es de una playlist. Abrí el video que querés y pegá el link de ese video."
    elif path.startswith(("/@", "/channel/", "/c/", "/user/")):
        return "Ese link es de un canal, no de un video. Entrá al video y pegá su link."
    elif path == "/results":
        return "Ese link es de una búsqueda de YouTube, no de un video."
    elif not path:
        return f"Ese link es la página principal de YouTube. Pegá el link de un video, por ejemplo: {_YOUTUBE_EXAMPLE}"

    if not video_id:
        return f"El link es de YouTube pero no apunta a un video. Tiene que verse como {_YOUTUBE_EXAMPLE}"
    if not _YOUTUBE_ID.match(video_id):
        return "El link parece incompleto: el identificador del video no es válido. Copialo de nuevo desde YouTube."
    return None


class IngestRequest(BaseModel):
    url: str
    # Empty means "use the video's own title"
    title: str = Field(default="", max_length=200)
    materia_id: str

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return v.strip()

    @field_validator("url")
    @classmethod
    def _youtube_only(cls, v: str) -> str:
        v = v.strip()
        error = youtube_url_error(v)
        if error:
            raise ValueError(error)
        # Accept links pasted without scheme ("www.youtube.com/watch?v=...")
        return v if "://" in v else f"https://{v}"


class IngestResponse(BaseModel):
    job_id: str


class IngestStatus(BaseModel):
    status: Literal["pending", "downloading", "transcribing", "extracting_frames", "analyzing_frames", "embedding", "done", "error"]
    message: str = ""
    progress: int = 0
    # Final class title (the video's title when the user left it empty), known after download
    title: str = ""


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

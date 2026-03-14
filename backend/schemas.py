from typing import Literal

from pydantic import BaseModel


class IngestRequest(BaseModel):
    url: str
    title: str
    class_id: str


class IngestResponse(BaseModel):
    job_id: str


class IngestStatus(BaseModel):
    status: Literal["pending", "downloading", "transcribing", "embedding", "done", "error"]
    message: str = ""
    progress: int = 0


class ClassInfo(BaseModel):
    class_id: str
    class_title: str
    source_url: str
    chunk_count: int


class ChatRequest(BaseModel):
    query: str
    class_id: str | None = None


class Source(BaseModel):
    class_title: str
    start_time: int
    end_time: int
    timestamp_link: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

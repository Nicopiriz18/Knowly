"""Ingest service: download audio, transcribe, chunk, embed, and store."""

import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import chromadb
import openai
import whisper

from config import settings
from schemas import IngestStatus

# In-memory job tracker
jobs: dict[str, IngestStatus] = {}


def _find_ytdlp() -> str:
    """Find yt-dlp executable: check venv Scripts dir first, then PATH."""
    venv_bin = Path(sys.executable).parent / "yt-dlp.exe"
    if venv_bin.exists():
        return str(venv_bin)
    venv_bin = Path(sys.executable).parent / "yt-dlp"
    if venv_bin.exists():
        return str(venv_bin)
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise RuntimeError("yt-dlp not found. Make sure it is installed and on PATH.")


def _download_audio(url: str, class_id: str) -> tuple[Path, str]:
    """Download audio using yt-dlp. Returns (audio_path, youtube_video_id)."""
    audio_dir = Path(settings.data_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{class_id}.mp3"
    ytdlp = _find_ytdlp()

    # Extract video info to get the YouTube video ID
    result = subprocess.run(
        [ytdlp, "--dump-json", "--no-download", url],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    video_id = info["id"]

    if output_path.exists():
        return output_path, video_id

    subprocess.run(
        [
            ytdlp,
            "-x",
            "--audio-format", "mp3",
            "-o", str(output_path),
            url,
        ],
        check=True,
    )
    return output_path, video_id


def _transcribe(audio_path: Path, class_id: str) -> list[dict]:
    """Transcribe audio with Whisper and return segments."""
    transcripts_dir = Path(settings.data_dir) / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcripts_dir / f"{class_id}.json"

    if transcript_path.exists():
        with open(transcript_path) as f:
            return json.load(f)

    model = whisper.load_model(settings.whisper_model)
    result = model.transcribe(str(audio_path), language=None)

    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    return segments


def _build_chunks(
    segments: list[dict],
    class_id: str,
    class_title: str,
    source_url: str,
    video_id: str,
) -> list[dict]:
    """Group segments into ~3-minute chunks."""
    chunks: list[dict] = []
    current_texts: list[str] = []
    chunk_start = segments[0]["start"] if segments else 0

    for seg in segments:
        current_texts.append(seg["text"])
        chunk_end = seg["end"]

        if chunk_end - chunk_start >= settings.chunk_duration:
            start_int = int(chunk_start)
            chunks.append(
                {
                    "class_id": class_id,
                    "class_title": class_title,
                    "source_url": source_url,
                    "start_time": start_int,
                    "end_time": int(chunk_end),
                    "text": " ".join(current_texts),
                    "timestamp_link": f"https://www.youtube.com/watch?v={video_id}&t={start_int}s",
                }
            )
            current_texts = []
            chunk_start = chunk_end

    # Remaining segments
    if current_texts:
        start_int = int(chunk_start)
        chunks.append(
            {
                "class_id": class_id,
                "class_title": class_title,
                "source_url": source_url,
                "start_time": start_int,
                "end_time": int(segments[-1]["end"]),
                "text": " ".join(current_texts),
                "timestamp_link": f"https://www.youtube.com/watch?v={video_id}&t={start_int}s",
            }
        )

    return chunks


def _embed_and_store(chunks: list[dict]) -> None:
    """Generate embeddings and store in ChromaDB."""
    client = openai.OpenAI(api_key=settings.openai_api_key)
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection("classes")

    texts = [c["text"] for c in chunks]

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    embeddings = [item.embedding for item in response.data]

    ids = [f"{chunks[i]['class_id']}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "class_id": c["class_id"],
            "class_title": c["class_title"],
            "source_url": c["source_url"],
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "timestamp_link": c["timestamp_link"],
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )


def run_ingest(job_id: str, url: str, title: str, class_id: str) -> None:
    """Run the full ingest pipeline, updating job status at each phase."""
    try:
        # Phase 1: Download
        jobs[job_id] = IngestStatus(status="downloading", message="Downloading audio...", progress=10)
        audio_path, video_id = _download_audio(url, class_id)

        # Phase 2: Transcribe
        jobs[job_id] = IngestStatus(status="transcribing", message="Transcribing audio...", progress=40)
        segments = _transcribe(audio_path, class_id)

        # Phase 3: Embed and store
        jobs[job_id] = IngestStatus(status="embedding", message="Building chunks and generating embeddings...", progress=70)
        chunks = _build_chunks(segments, class_id, title, url, video_id)
        _embed_and_store(chunks)

        # Done
        jobs[job_id] = IngestStatus(status="done", message=f"Ingested {len(chunks)} chunks successfully.", progress=100)

    except Exception as e:
        jobs[job_id] = IngestStatus(status="error", message=str(e), progress=0)


def start_ingest(job_id: str, url: str, title: str, class_id: str) -> None:
    """Start the ingest pipeline in a background thread."""
    jobs[job_id] = IngestStatus(status="pending", message="Job queued.", progress=0)
    thread = threading.Thread(target=run_ingest, args=(job_id, url, title, class_id), daemon=True)
    thread.start()

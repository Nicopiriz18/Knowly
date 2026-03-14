"""Pipeline: download audio → transcribe → chunk → embed → store in ChromaDB."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import chromadb
import openai
import whisper
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
AUDIO_DIR = DATA_DIR / "audio"
CHROMA_DIR = Path("chroma_db")
CHUNK_DURATION = 180  # 3 minutes in seconds


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
    print("Error: yt-dlp not found. Make sure the virtual environment is activated.")
    sys.exit(1)


def download_audio(url: str, class_id: str) -> tuple[Path, str]:
    """Download audio using yt-dlp. Returns (audio_path, youtube_video_id).

    Accepts YouTube URLs directly. Khan Academy videos are hosted on YouTube,
    so the user should provide the YouTube URL of the Khan Academy video.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    output_path = AUDIO_DIR / f"{class_id}.mp3"
    ytdlp = _find_ytdlp()

    # Extract video info to get the YouTube video ID
    print(f"Extracting video info from {url}...")
    result = subprocess.run(
        [ytdlp, "--dump-json", "--no-download", url],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(result.stdout)
    video_id = info["id"]
    print(f"YouTube video ID: {video_id}")

    if output_path.exists():
        print(f"Audio already exists: {output_path}")
        return output_path, video_id

    print("Downloading audio...")
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
    print(f"Audio saved: {output_path}")
    return output_path, video_id


def transcribe(audio_path: Path, class_id: str) -> list[dict]:
    """Transcribe audio with Whisper and return segments."""
    transcript_path = TRANSCRIPTS_DIR / f"{class_id}.json"
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    if transcript_path.exists():
        print(f"Transcript already exists: {transcript_path}")
        with open(transcript_path) as f:
            return json.load(f)

    print("Transcribing with Whisper (model: base)...")
    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), language=None)

    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result["segments"]
    ]

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    print(f"Transcript saved: {transcript_path} ({len(segments)} segments)")
    return segments


def build_chunks(
    segments: list[dict],
    class_id: str,
    class_title: str,
    source_url: str,
    video_id: str,
) -> list[dict]:
    """Group segments into ~3-minute chunks."""
    chunks = []
    current_texts: list[str] = []
    chunk_start = segments[0]["start"] if segments else 0

    for seg in segments:
        current_texts.append(seg["text"])
        chunk_end = seg["end"]

        if chunk_end - chunk_start >= CHUNK_DURATION:
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

    print(f"Created {len(chunks)} chunks (~{CHUNK_DURATION}s each)")
    return chunks


def embed_and_store(chunks: list[dict]) -> None:
    """Generate embeddings and store in ChromaDB."""
    client = openai.OpenAI()
    chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = chroma.get_or_create_collection("classes")

    texts = [c["text"] for c in chunks]
    print(f"Generating embeddings for {len(texts)} chunks...")

    # OpenAI allows batching up to 2048 inputs
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

    print(f"✅ Clase indexada: {len(chunks)} chunks guardados")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a Khan Academy class into Knowly")
    parser.add_argument("--url", required=True, help="YouTube URL of the Khan Academy video")
    parser.add_argument("--title", required=True, help='Class title, e.g. "Álgebra - Variables"')
    parser.add_argument("--class_id", required=True, help='Class ID, e.g. "algebra_01"')
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Check your .env file.")
        sys.exit(1)

    audio_path, video_id = download_audio(args.url, args.class_id)
    segments = transcribe(audio_path, args.class_id)
    chunks = build_chunks(segments, args.class_id, args.title, args.url, video_id)
    embed_and_store(chunks)


if __name__ == "__main__":
    main()

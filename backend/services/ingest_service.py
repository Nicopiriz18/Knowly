"""Ingest service: download media, transcribe, analyze video frames, chunk, embed, and store."""

import base64
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


def _find_ffmpeg() -> str:
    """Find ffmpeg executable on PATH."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RuntimeError("ffmpeg not found. Make sure it is installed and on PATH.")


def _download_media(url: str, class_id: str) -> tuple[Path, Path | None, str]:
    """Download media using yt-dlp.

    If video analysis is enabled, downloads video (480p max) and extracts audio.
    Otherwise downloads audio only.

    Returns (audio_path, video_path | None, youtube_video_id).
    """
    audio_dir = Path(settings.data_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{class_id}.mp3"
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

    if not settings.enable_video_analysis:
        # Audio-only download (original behavior)
        if not audio_path.exists():
            subprocess.run(
                [ytdlp, "-x", "--audio-format", "mp3", "-o", str(audio_path), url],
                check=True,
            )
        return audio_path, None, video_id

    # Video download path
    video_dir = Path(settings.data_dir) / "raw_videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_path = video_dir / f"{class_id}.mp4"

    if not video_path.exists():
        subprocess.run(
            [
                ytdlp,
                "-f", "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "--merge-output-format", "mp4",
                "-o", str(video_path),
                url,
            ],
            check=True,
        )

    # Extract audio from video with ffmpeg
    if not audio_path.exists():
        ffmpeg = _find_ffmpeg()
        subprocess.run(
            [ffmpeg, "-i", str(video_path), "-q:a", "0", "-map", "a", str(audio_path), "-y"],
            check=True,
        )

    return audio_path, video_path, video_id


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


def _extract_frames(video_path: Path, class_id: str, interval: int) -> list[dict]:
    """Extract frames from video at the given interval using ffmpeg.

    Returns list of {"path": Path, "timestamp": int}.
    """
    frames_dir = Path(settings.data_dir) / "frames" / class_id
    frames_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = _find_ffmpeg()
    subprocess.run(
        [
            ffmpeg, "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            str(frames_dir / "frame_%04d.png"),
            "-y",
        ],
        check=True,
    )

    frames = []
    for frame_file in sorted(frames_dir.glob("frame_*.png")):
        # frame_0001.png -> index 0 -> timestamp = 0 * interval
        index = int(frame_file.stem.split("_")[1]) - 1
        frames.append({"path": frame_file, "timestamp": index * interval})

    return frames


def _deduplicate_frames(frames: list[dict], threshold: int) -> list[dict]:
    """Remove visually similar consecutive frames using average perceptual hash.

    Keeps a frame only if its hamming distance from the previous kept frame
    exceeds the threshold.
    """
    from PIL import Image

    def average_hash(img_path: Path) -> int:
        """Compute a 64-bit average hash of an image."""
        img = Image.open(img_path).resize((8, 8)).convert("L")
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = 0
        for px in pixels:
            bits = (bits << 1) | (1 if px >= avg else 0)
        return bits

    def hamming_distance(a: int, b: int) -> int:
        return bin(a ^ b).count("1")

    if not frames:
        return []

    kept = [frames[0]]
    prev_hash = average_hash(frames[0]["path"])

    for frame in frames[1:]:
        current_hash = average_hash(frame["path"])
        if hamming_distance(prev_hash, current_hash) > threshold:
            kept.append(frame)
            prev_hash = current_hash

    return kept


def _analyze_frames(frames: list[dict], class_id: str) -> list[dict]:
    """Describe visual content of frames using Claude Vision.

    Processes frames in batches and caches results.
    Returns list of {"timestamp": int, "description": str}.
    """
    import anthropic

    visual_dir = Path(settings.data_dir) / "visual"
    visual_dir.mkdir(parents=True, exist_ok=True)
    cache_path = visual_dir / f"{class_id}.json"

    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    descriptions: list[dict] = []
    batch_size = 5

    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        content: list[dict] = []

        for frame in batch:
            with open(frame["path"], "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            minutes = frame["timestamp"] // 60
            seconds = frame["timestamp"] % 60
            content.append({
                "type": "text",
                "text": f"Frame en {minutes:02d}:{seconds:02d}:",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_data,
                },
            })

        content.append({
            "type": "text",
            "text": (
                "Describí de forma concisa el contenido visual educativo de cada frame "
                "(slides, formulas, codigo, diagramas, texto en pantalla). "
                "Si un frame no tiene contenido educativo relevante (ej: solo muestra al profesor), "
                "indicalo brevemente. Respondé en formato:\n"
                "MM:SS - descripcion\n"
                "para cada frame."
            ),
        })

        response = client.messages.create(
            model=settings.vision_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text
        # Parse response lines and match to batch frames
        for frame in batch:
            minutes = frame["timestamp"] // 60
            seconds = frame["timestamp"] % 60
            prefix = f"{minutes:02d}:{seconds:02d}"

            # Find the line matching this timestamp
            desc_line = ""
            for line in response_text.split("\n"):
                if prefix in line:
                    # Extract description after the timestamp prefix
                    parts = line.split(" - ", 1)
                    desc_line = parts[1].strip() if len(parts) > 1 else line.strip()
                    break

            if not desc_line:
                desc_line = "Sin contenido visual educativo relevante."

            descriptions.append({
                "timestamp": frame["timestamp"],
                "description": desc_line,
            })

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)

    return descriptions


def _merge_visual_descriptions(chunks: list[dict], descriptions: list[dict]) -> list[dict]:
    """Merge visual descriptions into chunk text based on timestamp overlap."""
    for chunk in chunks:
        matching = [
            d for d in descriptions
            if chunk["start_time"] <= d["timestamp"] < chunk["end_time"]
        ]
        if matching:
            visual_text = "\n".join(f"- {d['description']}" for d in matching)
            chunk["text"] += f"\n\n[Contenido visual en pantalla]\n{visual_text}"
    return chunks


def _build_chunks(
    segments: list[dict],
    class_id: str,
    class_title: str,
    source_url: str,
    video_id: str,
    materia_id: str = "",
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
                    "materia_id": materia_id,
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
                "materia_id": materia_id,
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
            "materia_id": c["materia_id"],
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


def _cleanup_video_files(class_id: str, video_path: Path | None) -> None:
    """Remove temporary video and frame files after processing."""
    if video_path and video_path.exists():
        video_path.unlink()

    frames_dir = Path(settings.data_dir) / "frames" / class_id
    if frames_dir.exists():
        shutil.rmtree(frames_dir)


def run_ingest(job_id: str, url: str, title: str, class_id: str, materia_id: str) -> None:
    """Run the full ingest pipeline, updating job status at each phase."""
    try:
        # Phase 1: Download
        jobs[job_id] = IngestStatus(status="downloading", message="Descargando media...", progress=10)
        audio_path, video_path, video_id = _download_media(url, class_id)

        # Phase 2: Transcribe
        jobs[job_id] = IngestStatus(status="transcribing", message="Transcribiendo audio...", progress=30)
        segments = _transcribe(audio_path, class_id)

        # Phase 3-4: Video analysis (if enabled)
        visual_descriptions: list[dict] = []
        if settings.enable_video_analysis and video_path is not None:
            # Phase 3: Extract frames
            jobs[job_id] = IngestStatus(status="extracting_frames", message="Extrayendo frames del video...", progress=45)
            frames = _extract_frames(video_path, class_id, settings.frame_interval)

            # Deduplicate
            frames = _deduplicate_frames(frames, settings.frame_similarity_threshold)

            # Phase 4: Analyze frames with vision
            jobs[job_id] = IngestStatus(status="analyzing_frames", message=f"Analizando {len(frames)} frames con vision...", progress=55)
            visual_descriptions = _analyze_frames(frames, class_id)

            # Cleanup video and frame files
            _cleanup_video_files(class_id, video_path)

        # Phase 5: Build chunks, merge visual descriptions, embed
        jobs[job_id] = IngestStatus(status="embedding", message="Generando embeddings...", progress=75)
        chunks = _build_chunks(segments, class_id, title, url, video_id, materia_id)

        if visual_descriptions:
            chunks = _merge_visual_descriptions(chunks, visual_descriptions)

        _embed_and_store(chunks)

        # Done
        jobs[job_id] = IngestStatus(status="done", message=f"Ingested {len(chunks)} chunks successfully.", progress=100)

    except Exception as e:
        jobs[job_id] = IngestStatus(status="error", message=str(e), progress=0)


def start_ingest(job_id: str, url: str, title: str, class_id: str, materia_id: str) -> None:
    """Start the ingest pipeline in a background thread."""
    jobs[job_id] = IngestStatus(status="pending", message="Job queued.", progress=0)
    thread = threading.Thread(target=run_ingest, args=(job_id, url, title, class_id, materia_id), daemon=True)
    thread.start()

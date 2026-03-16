from pathlib import Path

from pydantic_settings import BaseSettings

# Look for .env in parent directory (project root) when running locally
_env_file = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    chroma_dir: str = str(Path(__file__).resolve().parent.parent / "chroma_db")
    data_dir: str = str(Path(__file__).resolve().parent.parent / "data")
    chunk_duration: int = 180
    whisper_model: str = "base"
    # Video analysis
    enable_video_analysis: bool = True
    frame_interval: int = 30
    frame_similarity_threshold: int = 5
    vision_model: str = "claude-haiku-4-5-20251001"
    # Adaptive retrieval settings for broad queries
    broad_per_class_results: int = 10
    broad_n_results: int = 10
    broad_max_tokens: int = 4096
    max_context_chars: int = 80000

    class Config:
        env_file = str(_env_file)


settings = Settings()

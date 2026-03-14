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

    class Config:
        env_file = str(_env_file)


settings = Settings()

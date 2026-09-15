from pathlib import Path

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode

# Look for .env in parent directory (project root) when running locally
_env_file = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    openai_api_key: str
    anthropic_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "classes"
    data_dir: str = str(Path(__file__).resolve().parent.parent / "data")
    chunk_duration: int = 180
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

    # Auth
    jwt_secret: str
    jwt_expire_days: int = 7
    # Comma-separated list of admin emails. Admins are always approved.
    admin_emails: Annotated[list[str], NoDecode] = []
    otp_expire_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    # Email. If smtp_host is set, emails go to that SMTP server (MailDev in local dev,
    # or e.g. Gmail with an app password in production when smtp_username is set).
    # Otherwise they are sent through Resend; if resend_api_key is also empty, they are
    # printed to the console (dev only).
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    resend_api_key: str = ""
    email_from: str = "Knowly <onboarding@resend.dev>"
    frontend_url: str = "http://localhost:3000"

    # CORS: comma-separated list of allowed origins
    frontend_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Rate limits
    auth_start_limit_per_ip: int = 10  # per 10 minutes
    auth_verify_limit_per_ip: int = 20  # per 10 minutes
    chat_limit_per_hour: int = 60
    ingest_limit_per_day: int = 10

    @field_validator("admin_emails", mode="before")
    @classmethod
    def _parse_emails(cls, v):
        if isinstance(v, str):
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        return [e.strip().lower() for e in v]

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v

    class Config:
        env_file = str(_env_file)
        extra = "ignore"


settings = Settings()

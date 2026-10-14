"""PostHog AI Observability: one client shared by the chat and the ingest pipeline.

Without POSTHOG_PROJECT_TOKEN everything here is a no-op, so local development
works without a PostHog account.
"""

import hashlib

import anthropic
import openai
from posthog import Posthog

from config import settings

enabled = bool(settings.posthog_project_token)

posthog_client: Posthog | None = (
    Posthog(settings.posthog_project_token, host=settings.posthog_host) if enabled else None
)


def distinct_id(owner: str) -> str:
    """Stable anonymous id for a user, so the raw email never reaches PostHog."""
    return hashlib.sha256(owner.encode("utf-8")).hexdigest()


def anthropic_client() -> anthropic.Anthropic:
    """Anthropic client whose calls are captured when observability is on."""
    if not enabled:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    from posthog.ai.anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key, posthog_client=posthog_client)


def openai_client() -> openai.OpenAI:
    """OpenAI client whose calls are captured when observability is on."""
    if not enabled:
        return openai.OpenAI(api_key=settings.openai_api_key)
    from posthog.ai.openai import OpenAI

    return OpenAI(api_key=settings.openai_api_key, posthog_client=posthog_client)


def tracking_kwargs(owner: str, trace_id: str, **properties) -> dict:
    """Extra arguments for a wrapped client call. Privacy mode keeps the content
    (frame images, transcripts) out of PostHog; tokens, cost and latency are still sent."""
    if not enabled:
        return {}
    return {
        "posthog_distinct_id": distinct_id(owner),
        "posthog_trace_id": trace_id,
        "posthog_properties": properties,
        "posthog_privacy_mode": True,
    }

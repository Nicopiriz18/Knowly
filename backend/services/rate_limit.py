"""Minimal in-memory sliding-window rate limiter.

State lives in the process, so limits are per worker. Good enough for a single
uvicorn instance; move to Redis if the backend is scaled horizontally.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Record a hit for `key`; raise 429 if it exceeds `limit` within the window."""
    now = time.monotonic()
    with _lock:
        hits = _hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = int(hits[0] + window_seconds - now) + 1
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes. Probá de nuevo más tarde.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)

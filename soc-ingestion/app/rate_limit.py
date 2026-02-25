"""Simple Redis-backed sliding-window rate limiter."""

from __future__ import annotations

from fastapi import HTTPException

from .config import redis_client, settings


def check_rate_limit(key_hash: str) -> None:
    """Increment a per-minute counter keyed by the API-key hash.

    Raises ``429`` if the configured limit is exceeded.
    """
    key = f"rate:{key_hash}"
    current = redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, 60)

    if current > settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

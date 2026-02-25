"""API-key authentication — resolves the calling tenant."""

from __future__ import annotations

import hashlib

from fastapi import Header, HTTPException

from .config import db


def hash_key(key: str) -> str:
    """Return the SHA-256 hex digest of *key*."""
    return hashlib.sha256(key.encode()).hexdigest()


async def authenticate(x_api_key: str = Header(...)):
    """Dependency that validates ``X-API-Key`` and returns the api_keys record.

    The key is hashed with SHA-256 and looked up in the ``api_keys`` Mongo
    collection — the same approach used by the case-service.
    """
    key_hash = hash_key(x_api_key)
    record = db.api_keys.find_one({"key_hash": key_hash})

    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return record

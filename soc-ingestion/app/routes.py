"""Ingestion API routes."""

from __future__ import annotations

import gzip
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, Request
from pydantic import ValidationError

from .auth import authenticate, hash_key
from .config import db
from .kafka import publish
from .models import ActivityEvent
from .rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/logs")
async def ingest_logs(
    request: Request,
    api_record: dict = Depends(authenticate),
):
    """Accept a JSON array of ``ActivityEvent`` objects from the Security SDK.

    Steps:
    1. Authenticate via ``X-API-Key`` header.
    2. Rate-limit by API-key hash.
    3. Decompress body if ``Content-Encoding: gzip``.
    4. Validate each event, skip invalids.
    5. Publish as a ``{tenant_id, batch}`` envelope to Kafka ``raw-activity``.
    6. Record an ingestion metric in MongoDB.
    """
    tenant_id: str = api_record["tenant_id"]
    key_hash: str = api_record["key_hash"]

    # Rate-limit
    check_rate_limit(key_hash)

    # Read body — transparently handle gzip from the SDK
    raw_body = await request.body()
    content_encoding = request.headers.get("content-encoding", "")
    if content_encoding.lower() == "gzip":
        raw_body = gzip.decompress(raw_body)

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"accepted": 0, "errors": ["Invalid JSON body"]}

    # The SDK sends a JSON array of event dicts
    if not isinstance(payload, list):
        payload = [payload]

    # Validate each event individually so one bad apple doesn't spoil the batch
    valid_events: List[Dict[str, Any]] = []
    errors: List[str] = []
    for idx, raw_event in enumerate(payload):
        try:
            event = ActivityEvent.model_validate(raw_event)
            valid_events.append(event.model_dump(mode="json"))
        except (ValidationError, Exception) as exc:
            errors.append(f"event[{idx}]: {exc}")

    if valid_events:
        await publish(tenant_id, valid_events)

        # Record ingestion metric (best-effort)
        try:
            db.ingestion_metrics.update_one(
                {"tenant_id": tenant_id},
                {
                    "$set": {"last_event_at": datetime.now(timezone.utc)},
                    "$inc": {"total_events": len(valid_events)},
                    "$setOnInsert": {"tenant_id": tenant_id},
                },
                upsert=True,
            )
        except Exception:
            logger.exception("Failed to update ingestion_metrics")

    return {
        "accepted": len(valid_events),
        "errors": errors if errors else None,
    }

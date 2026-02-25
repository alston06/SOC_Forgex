"""Pydantic models for the Forgex Security SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    """A single activity / audit event to be ingested by the SOC platform.

    Required fields: ``timestamp``, ``event_type``, ``actor``, ``resource``,
    ``action``.  All other fields are optional but strongly recommended for
    richer detection coverage.
    """

    timestamp: datetime = Field(..., description="When the event occurred (UTC recommended)")
    event_type: str = Field(..., max_length=50, description="Category, e.g. 'http_request', 'user.login'")
    actor: str = Field(..., max_length=100, description="User or service identity")
    resource: str = Field(..., max_length=200, description="URL path or resource identifier")
    action: str = Field(..., max_length=50, description="HTTP method or action verb")
    source: str = Field(default="unknown", max_length=50, description="Origin system identifier")
    ip: Optional[str] = Field(None, max_length=45, description="Client IP (v4 or v6)")
    user_agent: Optional[str] = Field(None, max_length=500, description="HTTP User-Agent header")
    service_name: Optional[str] = Field(None, max_length=100, description="Producing service name")
    environment: Optional[str] = Field(None, max_length=20, description="Deployment environment")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")
    idempotency_key: Optional[str] = Field(None, max_length=100, description="For deduplication")

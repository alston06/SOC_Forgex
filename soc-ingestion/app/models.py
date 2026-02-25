"""Pydantic models for ingestion payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    """Matches the schema produced by the Security SDK."""

    timestamp: datetime = Field(...)
    event_type: str = Field(..., max_length=50)
    actor: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=200)
    action: str = Field(..., max_length=50)
    source: str = Field(default="unknown", max_length=50)
    ip: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)
    service_name: Optional[str] = Field(None, max_length=100)
    environment: Optional[str] = Field(None, max_length=20)
    extras: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(None, max_length=100)

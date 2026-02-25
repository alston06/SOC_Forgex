"""Pydantic models for activity events."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    """Raw activity event from ingestion."""

    timestamp: datetime
    event_type: str
    actor: str
    resource: str
    action: str
    ip: Optional[str] = None
    service_name: Optional[str] = None
    environment: Optional[str] = None
    extras: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""
        json_encoders = {datetime: lambda v: v.isoformat()}


class NormalizedActivityEvent(ActivityEvent):
    """Normalized and enriched activity event."""

    tenant_id: str
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None
    user_role: Optional[str] = None
    normalized_path: str
    risk_score: float = 0.0
    event_id: str

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

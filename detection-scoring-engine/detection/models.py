"""Pydantic models for detection events."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class NormalizedActivityEvent(BaseModel):
    """Normalized activity event from normalizer service."""

    timestamp: datetime
    event_type: str
    actor: str
    resource: str
    action: str
    ip: Optional[str] = None
    service_name: Optional[str] = None
    environment: Optional[str] = None
    extras: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: str
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None
    user_role: Optional[str] = None
    normalized_path: str
    risk_score: float = 0.0
    event_id: str

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class DetectionSeverity(str):
    """Severity levels for detections."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionStatus(str):
    """Status of detection."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class DetectionEvent(BaseModel):
    """Detection event from rule evaluation.

    Updated to match SPEC-AGENTS.md specification while maintaining
    backward compatibility with existing fields.
    """

    # Core identification (spec-compliant)
    detection_id: str
    tenant_id: str
    timestamp: datetime = Field(..., alias="detection_timestamp")  # Alias for backward compat

    # Rule information (spec-compliant)
    rule_id: str
    severity: str
    triggered_events: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str = Field(..., alias="rule_description")  # Alias for backward compat

    # New spec fields
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)

    # Legacy fields (kept for backward compatibility)
    rule_name: Optional[str] = None
    status: str = DetectionStatus.OPEN
    triggering_event: Optional[NormalizedActivityEvent] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    # Scoring (risk_score is separate from confidence)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}, "populate_by_name": True}

"""Shared Pydantic models for agents service."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectionEvent(BaseModel):
    """Detection event from detection engine (SPEC-AGENTS.md compliant)."""

    detection_id: str
    tenant_id: str
    timestamp: datetime
    triggered_events: List[str] = Field(default_factory=list)
    rule_id: str
    severity: str  # LOW|MEDIUM|HIGH|CRITICAL
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    description: str
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)

    # Optional legacy fields for compatibility
    risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[str] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class KickoffRequest(BaseModel):
    """Request to start a CrewAI flow."""

    detection: DetectionEvent


class KickoffResponse(BaseModel):
    """Response from kickoff endpoint."""

    flow_id: str
    status: str  # "started" | "already_started"


class CrewTaskContext(BaseModel):
    """Context for CrewAI task execution."""

    flow_id: str
    detection: DetectionEvent
    case_id: Optional[str] = None
    shared_state: Dict[str, Any] = Field(default_factory=dict)

"""Pydantic models for case service."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class CaseStatus(str):
    """Status of a case."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CaseSeverity(str):
    """Severity levels for cases."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseAction(str):
    """Action types for case operations."""

    OPEN = "open"
    UPDATE = "update"
    CLOSE = "close"


class AgentType(str):
    """Types of agents that can output to cases."""

    COMMANDER = "commander"
    TRIAGE = "triage"
    ANALYST = "analyst"
    INTEL = "intel"


class Case(BaseModel):
    """Case model representing an incident case."""

    case_id: str
    tenant_id: str
    detection_id: str
    severity: str
    summary: str
    status: str = CaseStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    agent_outputs: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class CaseActionRequest(BaseModel):
    """Request to perform an action on a case."""

    action: str  # "open" | "update" | "close"
    tenant_id: str
    detection_id: str
    severity: Optional[str] = None
    summary: Optional[str] = None
    case_id: Optional[str] = None


class CaseActionResponse(BaseModel):
    """Response from case action."""

    case_id: str
    status: str


class AgentOutputRequest(BaseModel):
    """Request to add agent output to a case."""

    case_id: str
    agent_type: str  # "commander" | "triage" | "analyst" | "intel"
    output: Dict[str, Any]


class AgentOutputResponse(BaseModel):
    """Response from agent output."""

    case_id: str
    status: str

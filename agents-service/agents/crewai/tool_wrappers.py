"""CrewAI-compatible synchronous tool wrappers.

These use synchronous ``requests`` calls so they work correctly when
CrewAI invokes them from inside an already-running asyncio event loop.
"""
import json
from typing import Any, Dict, Optional, Type
from datetime import datetime, timedelta

import requests
from crewai.tools import tool, BaseTool
from pydantic import BaseModel, Field
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

INTERNAL_HEADERS = {
    "Authorization": f"Bearer {settings.internal_auth_token}",
    "Content-Type": "application/json",
}

# ── Helper ────────────────────────────────────────────────────────────


def _post(url: str, payload: dict, timeout: float = 10.0) -> requests.Response:
    """Synchronous POST with internal auth."""
    resp = requests.post(url, headers=INTERNAL_HEADERS, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp


# ── Tools ─────────────────────────────────────────────────────────────


class _QueryLogsInput(BaseModel):
    tenant_id: str = Field(description="Tenant ID to query for")
    minutes_back: int = Field(default=30, description="Time window in minutes to look back")
    limit: int = Field(default=100, description="Maximum number of events to return")
    query_actor: str = Field(default="", description="Optional actor/user filter")
    query_ip: str = Field(default="", description="Optional source IP filter")
    query_normalized_path: str = Field(default="", description="Optional URL path filter")


class QueryLogsTool(BaseTool):
    name: str = "query_logs_sync"
    description: str = (
        "Query normalized logs from the normalizer service. "
        "Use this to retrieve recent security events for a tenant. "
        "Only tenant_id is required; all other arguments are optional filters."
    )
    args_schema: Type[BaseModel] = _QueryLogsInput

    def _run(
        self,
        tenant_id: str,
        minutes_back: int = 30,
        limit: int = 100,
        query_actor: str = "",
        query_ip: str = "",
        query_normalized_path: str = "",
    ) -> str:
        query: Dict[str, str] = {}
        if query_actor:
            query["actor"] = query_actor
        if query_ip:
            query["ip"] = query_ip
        if query_normalized_path:
            query["normalized_path"] = query_normalized_path

        now = datetime.utcnow()
        payload = {
            "tenant_id": tenant_id,
            "start_time": (now - timedelta(minutes=minutes_back)).isoformat(),
            "end_time": now.isoformat(),
            "query": query,
            "limit": limit,
        }

        try:
            url = f"{settings.normalizer_service_url}{settings.normalizer_log_query_endpoint}"
            resp = _post(url, payload)
            events = resp.json().get("events", [])
        except Exception as e:
            logger.error("Log query failed", error=str(e))
            events = []

        return json.dumps({
            "event_count": len(events),
            "events": events[:10],
            "truncated": len(events) > 10,
        }, indent=2, default=str)


query_logs_sync = QueryLogsTool()


@tool
def open_case_sync(
    tenant_id: str,
    detection_id: str,
    rule_id: str,
    severity: str = "MEDIUM",
    description: str = "",
) -> str:
    """Open a new case for a detection (CrewAI wrapper).

    Args:
        tenant_id: Tenant ID
        detection_id: Detection event ID
        rule_id: Rule that triggered the detection
        severity: Severity level (LOW|MEDIUM|HIGH|CRITICAL)
        description: Description of the case

    Returns:
        Case ID as string
    """
    payload = {
        "tenant_id": tenant_id,
        "detection_id": detection_id,
        "action": "open",
        "summary": description,
        "severity": severity,
    }

    try:
        url = f"{settings.case_service_url}{settings.case_action_endpoint}"
        resp = _post(url, payload)
        data = resp.json()
        case_id = data.get("case_id", data.get("incident_id", "unknown"))
        logger.info("Case opened", case_id=case_id, detection_id=detection_id)
        return str(case_id)
    except Exception as e:
        logger.error("Failed to open case", error=str(e))
        return f"error: {e}"


@tool
def update_case_sync(
    tenant_id: str,
    case_id: str,
    detection_id: str,
    new_severity: Optional[str] = None,
    new_summary: Optional[str] = None,
) -> str:
    """Update an existing case (CrewAI wrapper).

    Args:
        tenant_id: Tenant ID
        case_id: Case ID to update
        detection_id: Detection event ID
        new_severity: New severity level (optional)
        new_summary: New summary (optional)

    Returns:
        Confirmation message
    """
    payload: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "case_id": case_id,
        "detection_id": detection_id,
        "action": "update",
    }
    if new_severity:
        payload["severity"] = new_severity
    if new_summary:
        payload["summary"] = new_summary

    try:
        url = f"{settings.case_service_url}{settings.case_action_endpoint}"
        _post(url, payload)
        return f"Case {case_id} updated successfully"
    except Exception as e:
        logger.error("Failed to update case", error=str(e))
        return f"error: {e}"


@tool
def close_case_sync(
    tenant_id: str,
    case_id: str,
    detection_id: str,
) -> str:
    """Close an existing case (CrewAI wrapper).

    Args:
        tenant_id: Tenant ID
        case_id: Case ID to close
        detection_id: Detection event ID

    Returns:
        Confirmation message
    """
    payload = {
        "tenant_id": tenant_id,
        "case_id": case_id,
        "detection_id": detection_id,
        "action": "close",
    }

    try:
        url = f"{settings.case_service_url}{settings.case_action_endpoint}"
        _post(url, payload)
        return f"Case {case_id} closed successfully"
    except Exception as e:
        logger.error("Failed to close case", error=str(e))
        return f"error: {e}"


@tool
def store_agent_output_sync(
    case_id: str,
    agent_type: str,
    output_json: str,
) -> str:
    """Store agent output for a case (CrewAI wrapper).

    Args:
        case_id: Case ID to append output to
        agent_type: Type of agent (commander|triage|analyst|intel)
        output_json: JSON string of agent output

    Returns:
        Confirmation message
    """
    try:
        output_dict = json.loads(output_json)
    except json.JSONDecodeError:
        output_dict = {"raw_output": output_json}

    payload = {
        "case_id": case_id,
        "agent_type": agent_type,
        "output": output_dict,
    }

    try:
        url = f"{settings.case_service_url}{settings.agent_output_endpoint}"
        _post(url, payload)
        return f"Output from {agent_type} stored for case {case_id}"
    except Exception as e:
        logger.error("Failed to store agent output", error=str(e))
        return f"error: {e}"

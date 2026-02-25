"""CrewAI-compatible synchronous tool wrappers for async functions."""
import asyncio
import json
from typing import Any, Dict, Optional
from crewai.tools import tool
import structlog

from .tools.log_query import log_query_tool
from .tools.case_tool import case_tool_open, case_tool_update, case_tool_close
from .tools.agent_output import agent_output_tool
from .config import settings

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        logger.error("Async execution failed", error=str(e))
        raise


@tool
def query_logs_sync(
    tenant_id: str,
    minutes_back: int = 30,
    limit: int = 100,
    query_actor: Optional[str] = None,
    query_ip: Optional[str] = None,
    query_normalized_path: Optional[str] = None,
) -> str:
    """Query normalized logs from normalizer service (CrewAI wrapper).

    Args:
        tenant_id: Tenant ID to query for
        minutes_back: Time window in minutes to look back (default: 30)
        limit: Maximum number of events to return (default: 100)
        query_actor: Optional actor filter
        query_ip: Optional IP filter
        query_normalized_path: Optional path filter

    Returns:
        JSON string of log events for CrewAI consumption
    """
    query = {}
    if query_actor:
        query["actor"] = query_actor
    if query_ip:
        query["ip"] = query_ip
    if query_normalized_path:
        query["normalized_path"] = query_normalized_path

    events = run_async(log_query_tool(
        tenant_id=tenant_id,
        query=query,
        minutes_back=minutes_back,
        limit=limit,
    ))

    # Return as formatted string for CrewAI
    return json.dumps({
        "event_count": len(events),
        "events": events[:10],  # Limit for context window
        "truncated": len(events) > 10
    }, indent=2)


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
    detection_dict = {
        "detection_id": detection_id,
        "rule_id": rule_id,
        "severity": severity,
        "description": description,
    }

    case_id = run_async(case_tool_open(
        tenant_id=tenant_id,
        detection=detection_dict,
        summary=description,
        severity=severity,
    ))

    return case_id


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
    detection_dict = {"detection_id": detection_id}

    run_async(case_tool_update(
        tenant_id=tenant_id,
        case_id=case_id,
        detection=detection_dict,
        severity=new_severity,
        summary=new_summary,
    ))

    return f"Case {case_id} updated successfully"


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
    detection_dict = {"detection_id": detection_id}

    run_async(case_tool_close(
        tenant_id=tenant_id,
        case_id=case_id,
        detection=detection_dict,
    ))

    return f"Case {case_id} closed successfully"


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

    run_async(agent_output_tool(
        case_id=case_id,
        agent_type=agent_type,
        output=output_dict,
    ))

    return f"Output from {agent_type} stored for case {case_id}"

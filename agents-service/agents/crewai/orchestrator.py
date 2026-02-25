"""CrewAI flow orchestration logic."""
import uuid
import asyncio
from typing import Any, Dict
import structlog

from ..models import CrewTaskContext, DetectionEvent
from ..crewai.config import settings
from .tools.log_query import (
    log_query_tool,
    build_triage_query,
    build_analyst_query,
)
from .tools.case_tool import case_tool_open, case_tool_update
from .tools.agent_output import agent_output_tool

logger = structlog.get_logger(__name__)


async def triage_summarize(
    detection: DetectionEvent,
    triage_events: list,
) -> Dict[str, Any]:
    """Summarize triage analysis results (deterministic MVP implementation).

    Args:
        detection: DetectionEvent
        triage_events: List of log events from triage query

    Returns:
        Structured triage output
    """
    severity_count = len(triage_events)
    entities = detection.entities or {}
    evidence = detection.evidence or {}

    # Simple heuristic for severity upgrade
    suggested_severity = detection.severity
    if severity_count > 50:
        if detection.severity == "LOW":
            suggested_severity = "MEDIUM"
        elif detection.severity == "MEDIUM":
            suggested_severity = "HIGH"

    return {
        "summary": f"Triage completed with {severity_count} recent events analyzed.",
        "initial_severity": detection.severity,
        "suggested_severity": suggested_severity,
        "key_entities": list(set(
            (entities.get("actor", []) or [])
            + (entities.get("ip", []) or [])
        )),
        "event_count": severity_count,
        "notes": f"Analyzed events from last 30 minutes for {detection.tenant_id}.",
    }


async def analyst_summarize(
    detection: DetectionEvent,
    analyst_events: list,
) -> Dict[str, Any]:
    """Summarize incident analysis results (deterministic MVP implementation).

    Args:
        detection: DetectionEvent
        analyst_events: List of log events from analyst query

    Returns:
        Structured incident analysis output
    """
    unique_actors = set()
    unique_ips = set()
    unique_paths = set()

    for event in analyst_events:
        if "actor" in event:
            unique_actors.add(event["actor"])
        if "ip" in event:
            unique_ips.add(event["ip"])
        if "normalized_path" in event:
            unique_paths.add(event["normalized_path"])

    entities = detection.entities or {}

    return {
        "summary": (
            f"Incident analysis completed over 24-hour window. "
            f"Found {len(unique_actors)} unique actors, "
            f"{len(unique_ips)} unique IPs, "
            f"{len(unique_paths)} unique endpoints."
        ),
        "blast_radius": {
            "affected_actors": len(unique_actors),
            "affected_ips": len(unique_ips),
            "affected_endpoints": len(unique_paths),
        },
        "pattern_analysis": {
            "primary_actor": entities.get("actor", [None])[0],
            "primary_ip": entities.get("ip", [None])[0],
        },
        "event_count": len(analyst_events),
        "notes": "Analysis based on 24-hour log window. No external threat intelligence integrated yet.",
    }


async def intel_summarize(
    detection: DetectionEvent,
    triage_events: list,
    analyst_events: list,
) -> Dict[str, Any]:
    """Summarize threat intelligence (deterministic MVP implementation).

    Args:
        detection: DetectionEvent
        triage_events: List of recent log events
        analyst_events: List of 24h log events

    Returns:
        Structured threat intelligence output
    """
    entities = detection.entities or {}
    evidence = detection.evidence or {}

    # Check for known bad patterns (simple heuristic)
    ips = entities.get("ip", [])
    threat_indicators = []

    if ips:
        # Check for multiple IPs (possible attack from multiple sources)
        if len(ips) > 3:
            threat_indicators.append("Multiple source IPs detected")

        # Check for repeated failures (simple check)
        for ip in ips:
            # In a real implementation, this would query a threat intel database
            pass

    return {
        "summary": "Threat intelligence analysis completed using internal log data.",
        "known_bad_indicators": threat_indicators,
        "threat_level": "MEDIUM" if threat_indicators else "LOW",
        "enrichment": {
            "source_ips": ips,
            "actor_count": len(entities.get("actor", [])),
        },
        "notes": "Threat intelligence limited to internal log analysis. External feeds not integrated yet.",
    }


async def run_flow_for_detection(context: CrewTaskContext) -> None:
    """Run the full CrewAI analysis flow for a detection.

    This is a deterministic MVP implementation using async Python functions
    instead of the full CrewAI framework (which is synchronous).

    Flow:
    1. Orchestrator opens case
    2. Triage Analyst queries logs (15-30min window)
    3. If severity upgrade, Orchestrator updates case
    4. Incident Analyst queries logs (24h window)
    5. Threat Intel summarizes threats
    6. Orchestrator finalizes (no auto-close for MVP)
    """
    detection_dict = context.detection.model_dump(mode="json")
    detection = context.detection

    try:
        # Step 1: Orchestrator opens case
        logger.info(
            "Opening case for detection",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
        )

        summary = detection.description or f"Alert {detection.rule_id} triggered"
        case_id = await case_tool_open(
            tenant_id=detection.tenant_id,
            detection=detection_dict,
            summary=summary,
            severity=detection.severity,
        )
        context.case_id = case_id

        # Orchestrator initial output
        await agent_output_tool(
            case_id=case_id,
            agent_type="commander",
            output={
                "flow_id": context.flow_id,
                "initial_summary": summary,
                "rule_id": detection.rule_id,
                "severity": detection.severity,
                "confidence": detection.confidence,
            },
        )

        # Step 2: Triage Analyst
        logger.info(
            "Running triage analysis",
            flow_id=context.flow_id,
            case_id=case_id,
        )

        triage_query = build_triage_query(detection_dict)
        triage_events = await log_query_tool(
            tenant_id=detection.tenant_id,
            query=triage_query,
            minutes_back=30,
            limit=200,
        )

        triage_output = await triage_summarize(detection, triage_events)
        await agent_output_tool(case_id=case_id, agent_type="triage", output=triage_output)

        # Step 3: Update case if severity upgraded
        suggested_severity = triage_output.get("suggested_severity")
        if suggested_severity and suggested_severity != detection.severity:
            logger.info(
                "Severity upgrade recommended",
                flow_id=context.flow_id,
                from_severity=detection.severity,
                to_severity=suggested_severity,
            )

            await case_tool_update(
                tenant_id=detection.tenant_id,
                case_id=case_id,
                detection=detection_dict,
                severity=suggested_severity,
                summary=f"{summary} (severity upgraded to {suggested_severity})",
            )

        # Step 4: Incident Analyst
        logger.info(
            "Running incident analysis",
            flow_id=context.flow_id,
            case_id=case_id,
        )

        analyst_query = build_analyst_query(detection_dict)
        analyst_events = await log_query_tool(
            tenant_id=detection.tenant_id,
            query=analyst_query,
            minutes_back=24 * 60,
            limit=1000,
        )

        analyst_output = await analyst_summarize(detection, analyst_events)
        await agent_output_tool(case_id=case_id, agent_type="analyst", output=analyst_output)

        # Step 5: Threat Intel
        logger.info(
            "Running threat intelligence analysis",
            flow_id=context.flow_id,
            case_id=case_id,
        )

        intel_output = await intel_summarize(detection, triage_events, analyst_events)
        await agent_output_tool(case_id=case_id, agent_type="intel", output=intel_output)

        # Step 6: Orchestrator finalizes (no auto-close for MVP)
        logger.info(
            "Flow completed",
            flow_id=context.flow_id,
            case_id=case_id,
        )

        await agent_output_tool(
            case_id=case_id,
            agent_type="commander",
            output={
                "flow_id": context.flow_id,
                "final_status": "completed",
                "notes": "All agents completed analysis. Case remains open for human review.",
            },
        )

    except Exception as e:
        logger.error(
            "Error in CrewAI flow",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
            error=str(e),
        )
        # Store error as agent output
        if context.case_id:
            try:
                await agent_output_tool(
                    case_id=context.case_id,
                    agent_type="commander",
                    output={
                        "flow_id": context.flow_id,
                        "error": str(e),
                        "status": "failed",
                    },
                )
            except Exception:
                # Best effort to store error
                pass

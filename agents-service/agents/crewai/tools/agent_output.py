"""AgentOutputTool for CrewAI agents."""
from typing import Any, Dict
import httpx
import structlog

from ...crewai.config import settings

logger = structlog.get_logger(__name__)

INTERNAL_HEADERS = {
    "Authorization": f"Bearer {settings.internal_auth_token}",
    "Content-Type": "application/json",
}


async def agent_output_tool(
    case_id: str,
    agent_type: str,
    output: Dict[str, Any],
) -> None:
    """Store agent output for a case.

    Args:
        case_id: Case ID to append output to
        agent_type: Type of agent producing the output
            - "commander" (Orchestrator)
            - "triage" (Triage Analyst)
            - "analyst" (Incident Analyst)
            - "intel" (Threat Intel)
        output: Structured output from the agent (will be stored as JSON)
    """
    payload = {
        "case_id": case_id,
        "agent_type": agent_type,
        "output": output,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{settings.case_service_url}{settings.agent_output_endpoint}"
            resp = await client.post(url, headers=INTERNAL_HEADERS, json=payload)
            resp.raise_for_status()

            logger.info(
                "Agent output stored",
                case_id=case_id,
                agent_type=agent_type,
            )

        except httpx.HTTPError as e:
            logger.error(
                "Failed to store agent output",
                case_id=case_id,
                agent_type=agent_type,
                error=str(e),
            )
            raise

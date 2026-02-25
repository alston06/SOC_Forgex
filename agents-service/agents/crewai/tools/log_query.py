"""LogQueryTool for CrewAI agents."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx
import structlog

from ...crewai.config import settings

logger = structlog.get_logger(__name__)

INTERNAL_HEADERS = {
    "Authorization": f"Bearer {settings.internal_auth_token}",
    "Content-Type": "application/json",
}


async def log_query_tool(
    tenant_id: str,
    query: dict,
    minutes_back: int = 60,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query normalized logs from normalizer service.

    Args:
        tenant_id: Tenant ID to query for
        query: Query dict (e.g., {"actor": "user123", "normalized_path": "/api/users/{id}"})
        minutes_back: Time window in minutes to look back
        limit: Maximum number of events to return

    Returns:
        List of NormalizedActivityEvent objects
    """
    now = datetime.utcnow()
    time_from = (now - timedelta(minutes=minutes_back)).isoformat() + "Z"
    time_to = now.isoformat() + "Z"

    payload = {
        "tenant_id": tenant_id,
        "query": query,
        "time_from": time_from,
        "time_to": time_to,
        "limit": limit,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{settings.normalizer_service_url}{settings.normalizer_log_query_endpoint}"
            resp = await client.post(url, headers=INTERNAL_HEADERS, json=payload)
            resp.raise_for_status()
            data = resp.json()

            logger.info(
                "Log query executed",
                tenant_id=tenant_id,
                minutes_back=minutes_back,
                event_count=len(data.get("events", [])),
            )

            return data.get("events", [])

        except httpx.HTTPError as e:
            logger.error("Log query failed", error=str(e))
            return []
        except Exception as e:
            logger.error("Unexpected error in log query", error=str(e))
            return []


def build_triage_query(detection: Dict[str, Any]) -> Dict[str, str]:
    """Build a log query for triage analysis (15-30min window).

    Priority order:
    1. entities.actor[0] if available
    2. entities.ip[0] if available
    3. evidence.normalized_path if available
    4. Broad query by tenant_id only
    """
    entities = detection.get("entities", {})
    evidence = detection.get("evidence", {})

    # Try actor first
    if actors := entities.get("actor"):
        if actors and actors[0]:
            return {"actor": actors[0]}

    # Try IP
    if ips := entities.get("ip"):
        if ips and ips[0]:
            return {"ip": ips[0]}

    # Try normalized path from evidence
    if normalized_path := evidence.get("normalized_path"):
        return {"normalized_path": normalized_path}

    # Fallback: return empty query (all events for tenant)
    return {}


def build_analyst_query(detection: Dict[str, Any]) -> Dict[str, str]:
    """Build a broad log query for incident analysis (24h window).

    Tries to combine multiple fields for a comprehensive query.
    """
    entities = detection.get("entities", {})
    evidence = detection.get("evidence", {})
    query = {}

    if actors := entities.get("actor"):
        if actors and actors[0]:
            query["actor"] = actors[0]

    if ips := entities.get("ip"):
        if ips and ips[0]:
            query["ip"] = ips[0]

    if normalized_path := evidence.get("normalized_path"):
        query["normalized_path"] = normalized_path

    return query

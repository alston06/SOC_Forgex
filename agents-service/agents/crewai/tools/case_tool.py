"""CaseTool for CrewAI agents."""
from typing import Any, Dict, Optional
import httpx
import structlog

from ...crewai.config import settings

logger = structlog.get_logger(__name__)

INTERNAL_HEADERS = {
    "Authorization": f"Bearer {settings.internal_auth_token}",
    "Content-Type": "application/json",
}


async def case_tool_open(
    tenant_id: str,
    detection: Dict[str, Any],
    summary: str,
    severity: Optional[str] = None,
) -> str:
    """Open a new case for a detection.

    Args:
        tenant_id: Tenant ID
        detection: DetectionEvent dict
        summary: Case summary description
        severity: Optional severity override (defaults to detection severity)

    Returns:
        case_id: The ID of the created case
    """
    payload = {
        "action": "open",
        "tenant_id": tenant_id,
        "detection_id": detection.get("detection_id"),
        "severity": severity or detection.get("severity", "MEDIUM"),
        "summary": summary,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{settings.case_service_url}{settings.case_action_endpoint}"
            resp = await client.post(url, headers=INTERNAL_HEADERS, json=payload)
            resp.raise_for_status()
            data = resp.json()

            logger.info(
                "Case opened",
                tenant_id=tenant_id,
                detection_id=detection.get("detection_id"),
                case_id=data.get("case_id"),
                severity=severity or detection.get("severity"),
            )

            return data["case_id"]

        except httpx.HTTPError as e:
            logger.error("Failed to open case", error=str(e))
            raise


async def case_tool_update(
    tenant_id: str,
    case_id: str,
    detection: Dict[str, Any],
    severity: Optional[str] = None,
    summary: Optional[str] = None,
) -> None:
    """Update an existing case.

    Args:
        tenant_id: Tenant ID
        case_id: Case ID to update
        detection: DetectionEvent dict
        severity: Optional new severity
        summary: Optional new summary
    """
    payload = {
        "action": "update",
        "tenant_id": tenant_id,
        "detection_id": detection.get("detection_id"),
        "case_id": case_id,
    }

    if severity:
        payload["severity"] = severity
    if summary:
        payload["summary"] = summary

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{settings.case_service_url}{settings.case_action_endpoint}"
            resp = await client.post(url, headers=INTERNAL_HEADERS, json=payload)
            resp.raise_for_status()

            logger.info(
                "Case updated",
                case_id=case_id,
                severity=severity,
            )

        except httpx.HTTPError as e:
            logger.error("Failed to update case", error=str(e))
            raise


async def case_tool_close(
    tenant_id: str,
    case_id: str,
    detection: Dict[str, Any],
) -> None:
    """Close an existing case.

    Args:
        tenant_id: Tenant ID
        case_id: Case ID to close
        detection: DetectionEvent dict
    """
    payload = {
        "action": "close",
        "tenant_id": tenant_id,
        "detection_id": detection.get("detection_id"),
        "case_id": case_id,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            url = f"{settings.case_service_url}{settings.case_action_endpoint}"
            resp = await client.post(url, headers=INTERNAL_HEADERS, json=payload)
            resp.raise_for_status()

            logger.info("Case closed", case_id=case_id)

        except httpx.HTTPError as e:
            logger.error("Failed to close case", error=str(e))
            raise

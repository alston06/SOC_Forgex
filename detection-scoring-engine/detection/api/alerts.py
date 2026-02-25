"""Alerts API for querying detections."""
from datetime import datetime, timedelta, timezone
from typing import List

import structlog
from fastapi import APIRouter, Query, HTTPException, Request
from opensearchpy.exceptions import NotFoundError

from ..config import settings
from ..models import DetectionEvent

logger = structlog.get_logger(__name__)

router = APIRouter()


def _indices_for_range(tenant_id: str, time_from: datetime, time_to: datetime) -> List[str]:
    """Generate index names for a date range.

    Args:
        tenant_id: Tenant identifier.
        time_from: Start of time range.
        time_to: End of time range.

    Returns:
        List of index names in format detections-{tenant_id}-{YYYY-MM}.
    """
    indices = set()
    current = datetime(time_from.year, time_from.month, 1, tzinfo=time_from.tzinfo)

    while current <= time_to:
        month = current.strftime("%Y-%m")
        indices.add(f"{settings.detection_index_prefix}{tenant_id}-{month}")

        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1, tzinfo=current.tzinfo)
        else:
            current = datetime(current.year, current.month + 1, 1, tzinfo=current.tzinfo)

    return sorted(indices)


@router.get("/v1/alerts", response_model=List[DetectionEvent])
async def get_alerts(
    tenant_id: str = Query(..., description="Tenant ID (required)"),
    since: str = Query(
        default=None,
        description="ISO8601 timestamp for start of time range (default: 24 hours ago)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of results (default: 50, max: 200)",
    ),
    rule_id: str = Query(
        default=None,
        description="Filter by rule ID",
    ),
    severity: str = Query(
        default=None,
        description="Filter by severity (low, medium, high, critical)",
    ),
    request: Request = None,
) -> List[DetectionEvent]:
    """Query detection alerts from OpenSearch.

    Args:
        tenant_id: Tenant identifier (required)
        since: ISO8601 timestamp for time range start (default: now-24h)
        limit: Maximum number of results (default: 50, max: 200)
        rule_id: Optional filter by rule ID
        severity: Optional filter by severity level
        request: FastAPI request object

    Returns:
        List of matching detection events
    """
    client = request.app.state.opensearch

    # Parse time range
    if since:
        try:
            time_from = datetime.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' timestamp format")
    else:
        time_from = datetime.now(timezone.utc) - timedelta(hours=24)

    time_to = datetime.now(timezone.utc)

    # Build OpenSearch query
    must = [
        {"term": {"tenant_id": tenant_id}},
        {
            "range": {
                "detection_timestamp": {
                    "gte": time_from.isoformat(),
                    "lte": time_to.isoformat(),
                }
            }
        },
    ]

    if rule_id:
        must.append({"term": {"rule_id": rule_id}})

    if severity:
        must.append({"term": {"severity": severity}})

    query = {"bool": {"must": must}}

    # Get indices for the time range
    indices = _indices_for_range(tenant_id, time_from, time_to)

    logger.debug(
        "Querying alerts",
        tenant_id=tenant_id,
        indices=indices,
        since=time_from.isoformat(),
        limit=limit,
        rule_id=rule_id,
        severity=severity,
    )

    try:
        res = client.search(
            index=",".join(indices),
            body={
                "query": query,
                "size": limit,
                "sort": [{"detection_timestamp": {"order": "desc"}}],
            },
        )
    except NotFoundError:
        logger.debug("No indices found for time range", tenant_id=tenant_id, indices=indices)
        return []

    detections = []
    for hit in res.get("hits", {}).get("hits", []):
        source = hit["_source"]
        detections.append(DetectionEvent(**source))

    logger.info(
        "Alerts query completed",
        tenant_id=tenant_id,
        result_count=len(detections),
    )

    return detections

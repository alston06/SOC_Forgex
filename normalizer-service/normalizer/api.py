"""Internal API for querying normalized logs."""
from datetime import datetime
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from opensearchpy.exceptions import NotFoundError
from pydantic import BaseModel

from .config import settings
from .models import NormalizedActivityEvent

logger = structlog.get_logger(__name__)

router = APIRouter()


async def internal_auth(authorization: str = Header(...)) -> None:
    """Dependency to verify internal authentication token.

    Args:
        authorization: Authorization header value.

    Raises:
        HTTPException: If token is missing or invalid.
    """
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization[len(prefix):]
    if token != settings.internal_auth_token:
        raise HTTPException(status_code=403, detail="Forbidden")


class LogQuery(BaseModel):
    """Request model for log queries."""

    tenant_id: str
    query: Dict[str, Any] = {}
    time_from: datetime
    time_to: datetime
    limit: int = 100


class LogQueryResponse(BaseModel):
    """Response model for log queries."""

    events: List[NormalizedActivityEvent]


def _indices_for_range(tenant_id: str, time_from: datetime, time_to: datetime) -> List[str]:
    """Generate index names for a date range.

    Args:
        tenant_id: Tenant identifier.
        time_from: Start of time range.
        time_to: End of time range.

    Returns:
        List of index names in format logs-{tenant_id}-{YYYY-MM}.
    """
    indices = set()
    current = datetime(time_from.year, time_from.month, 1, tzinfo=time_from.tzinfo)

    while current <= time_to:
        month = current.strftime("%Y-%m")
        indices.add(f"logs-{tenant_id}-{month}")

        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1, tzinfo=current.tzinfo)
        else:
            current = datetime(current.year, current.month + 1, 1, tzinfo=current.tzinfo)

    return sorted(indices)


@router.post("/query-logs", response_model=LogQueryResponse, dependencies=[Depends(internal_auth)])
async def query_logs(payload: LogQuery, request: Request) -> LogQueryResponse:
    """Query normalized logs from OpenSearch.

    Supported filters in payload.query:
        - actor: Exact match
        - normalized_path: Exact match
        - service_name: Exact match
        - event_type: Exact match

    Args:
        payload: Query parameters including tenant_id, filters, time range, and limit.
        request: FastAPI request object (for accessing app state).

    Returns:
        Matching normalized events.
    """
    client = request.app.state.opensearch
    tenant_id = payload.tenant_id

    # Build OpenSearch query
    must = [
        {"term": {"tenant_id": tenant_id}},
        {
            "range": {
                "timestamp": {
                    "gte": payload.time_from.isoformat(),
                    "lte": payload.time_to.isoformat(),
                }
            }
        },
    ]

    for field in ["actor", "normalized_path", "service_name", "event_type"]:
        value = payload.query.get(field)
        if value:
            must.append({"term": {field: value}})

    query = {"bool": {"must": must}}

    # Get indices for the time range
    indices = _indices_for_range(tenant_id, payload.time_from, payload.time_to)

    logger.debug(
        "Querying logs",
        tenant_id=tenant_id,
        indices=indices,
        filters=payload.query,
        limit=payload.limit,
    )

    try:
        res = client.search(
            index=",".join(indices),
            body={
                "query": query,
                "size": payload.limit,
                "sort": [{"timestamp": {"order": "desc"}}],
            },
        )
    except NotFoundError:
        # No indices exist for this time range, return empty results
        logger.debug("No indices found for time range", tenant_id=tenant_id, indices=indices)
        return LogQueryResponse(events=[])

    events = []
    for hit in res.get("hits", {}).get("hits", []):
        source = hit["_source"]
        events.append(NormalizedActivityEvent(**source))

    logger.info(
        "Log query completed",
        tenant_id=tenant_id,
        result_count=len(events),
    )

    return LogQueryResponse(events=events)

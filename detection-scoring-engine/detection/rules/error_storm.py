"""Error Storm Detection Rule."""
from datetime import timedelta
from typing import Optional

import structlog
from opensearchpy import OpenSearch

from .base import BaseRule
from ..models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity

logger = structlog.get_logger(__name__)

# HTTP 5xx status codes
HTTP_5XX_CODES = {"500", "501", "502", "503", "504", "505", "506", "507", "508", "510", "511"}


class ErrorStormRule(BaseRule):
    """Detect error storms: >=50 5xx errors for same (ip, normalized_path) in 10min."""

    def __init__(self):
        super().__init__(
            rule_id="error-storm-001",
            rule_name="HTTP Error Storm",
            rule_description="High volume of HTTP 5xx errors from same IP and endpoint",
            severity=DetectionSeverity.MEDIUM,
        )

    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
        normalized_index_prefix: str,
    ) -> Optional[DetectionEvent]:
        # Only evaluate HTTP events
        if event.event_type != "http":
            return None

        # Extract status code from extras
        status_code = None
        if event.extras:
            status_code = str(event.extras.get("status_code", ""))

        if not status_code or status_code not in HTTP_5XX_CODES:
            return None

        if not event.ip or not event.normalized_path:
            logger.debug("Missing IP or path for error storm check", event_id=event.event_id)
            return None

        # Query for 5xx errors in last 10 minutes
        time_window = timedelta(minutes=10)
        time_from = event.timestamp - time_window
        time_to = event.timestamp

        index_pattern = f"{normalized_index_prefix}{event.tenant_id}-*"

        query = {
            "bool": {
                "must": [
                    {"term": {"tenant_id": event.tenant_id}},
                    {"term": {"event_type": "http"}},
                    {"term": {"ip": event.ip}},
                    {"term": {"normalized_path": event.normalized_path}},
                    {"term": {"extras.status_code": status_code}},
                    {
                        "range": {
                            "timestamp": {
                                "gte": time_from.isoformat(),
                                "lte": time_to.isoformat(),
                            }
                        }
                    },
                ]
            }
        }

        errors = await self.query_opensearch(
            opensearch,
            index_pattern,
            query,
            size=200,  # Larger size for counting
        )

        if len(errors) >= 50:
            logger.info(
                "Error storm detected",
                ip=event.ip,
                path=event.normalized_path,
                status_code=status_code,
                error_count=len(errors),
                event_id=event.event_id,
            )

            context = {
                "error_count": len(errors),
                "time_window_minutes": 10,
                "ip": event.ip,
                "normalized_path": event.normalized_path,
                "status_code": status_code,
                "actor": event.actor,
            }

            # Risk score based on error count
            risk_score = min(0.85, 0.5 + (len(errors) / 200))

            return self.create_detection(event, context=context, risk_score=risk_score)

        return None

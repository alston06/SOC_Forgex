"""Brute Force Login Detection Rule."""
from datetime import timedelta
from typing import Optional

import structlog
from opensearchpy import OpenSearch

from .base import BaseRule
from ..models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity

logger = structlog.get_logger(__name__)


class BruteForceRule(BaseRule):
    """Detect brute force login attempts: >=5 failed logins for same (actor, ip) in 5min."""

    def __init__(self):
        super().__init__(
            rule_id="brute-force-001",
            rule_name="Brute Force Login Attempt",
            rule_description="Multiple failed login attempts from same user and IP address",
            severity=DetectionSeverity.HIGH,
        )

    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
        normalized_index_prefix: str,
    ) -> Optional[DetectionEvent]:
        # Only evaluate failed login events
        if event.event_type != "auth" or event.action != "login_failed":
            return None

        if not event.actor or not event.ip:
            logger.debug("Missing actor or IP for brute force check", event_id=event.event_id)
            return None

        # Query OpenSearch for failed logins in last 5 minutes
        time_window = timedelta(minutes=5)
        time_from = event.timestamp - time_window
        time_to = event.timestamp

        index_pattern = f"{normalized_index_prefix}{event.tenant_id}-*"

        query = {
            "bool": {
                "must": [
                    {"match": {"tenant_id": event.tenant_id}},
                    {"match": {"event_type": "auth"}},
                    {"match": {"action": "login_failed"}},
                    {"match": {"actor": event.actor}},
                    {"match": {"ip": event.ip}},
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

        failed_logins = await self.query_opensearch(
            opensearch,
            index_pattern,
            query,
            size=100,
        )

        if len(failed_logins) >= 5:
            logger.info(
                "Brute force detected",
                actor=event.actor,
                ip=event.ip,
                count=len(failed_logins),
                event_id=event.event_id,
            )

            context = {
                "failed_login_count": len(failed_logins),
                "time_window_minutes": 5,
                "actor": event.actor,
                "ip": event.ip,
                "recent_failed_logins": [
                    {"timestamp": hit["timestamp"], "event_id": hit["event_id"]}
                    for hit in failed_logins[:10]  # Last 10
                ],
            }

            # Risk score: scales with attempt count
            risk_score = min(0.9, 0.5 + (len(failed_logins) / 50))
            # Confidence: slow scale so 100 attempts → ~0.73, caps at 0.85
            # (query size limit means count is always 5–100)
            confidence = min(0.85, 0.60 + len(failed_logins) / 800)

            return self.create_detection(event, context=context, risk_score=risk_score, confidence=confidence)

        return None

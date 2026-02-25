"""Admin Abuse Detection Rule."""
from datetime import timedelta
from typing import Optional

import structlog
from opensearchpy import OpenSearch

from .base import BaseRule
from ..models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity

logger = structlog.get_logger(__name__)

# Define what counts as an admin action
ADMIN_ACTIONS = {
    "user_create",
    "user_delete",
    "user_role_change",
    "config_modify",
    "data_delete",
    "export_all",
}


class AdminAbuseRule(BaseRule):
    """Detect non-admin users performing admin actions: >=10 admin actions in 1 hour."""

    def __init__(self):
        super().__init__(
            rule_id="admin-abuse-001",
            rule_name="Admin Abuse by Non-Admin",
            rule_description="Non-admin user performing excessive admin actions",
            severity=DetectionSeverity.HIGH,
        )

    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
        normalized_index_prefix: str,
    ) -> Optional[DetectionEvent]:
        # Check if this is an admin action
        if event.action not in ADMIN_ACTIONS:
            return None

        # Check if user is actually an admin
        if event.user_role == "admin":
            return None

        if not event.actor:
            logger.debug("Missing actor for admin abuse check", event_id=event.event_id)
            return None

        # Query for admin actions in last 1 hour
        time_window = timedelta(hours=1)
        time_from = event.timestamp - time_window
        time_to = event.timestamp

        index_pattern = f"{normalized_index_prefix}{event.tenant_id}-*"

        query = {
            "bool": {
                "must": [
                    {"match": {"tenant_id": event.tenant_id}},
                    {"match": {"actor": event.actor}},
                    {"bool": {"should": [{"match": {"action": a}} for a in ADMIN_ACTIONS], "minimum_should_match": 1}},
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

        admin_actions = await self.query_opensearch(
            opensearch,
            index_pattern,
            query,
            size=200,  # Larger size for counting
        )

        if len(admin_actions) >= 10:
            logger.info(
                "Admin abuse detected",
                actor=event.actor,
                role=event.user_role,
                action_count=len(admin_actions),
                event_id=event.event_id,
            )

            # Count by action type
            action_counts = {}
            for action_event in admin_actions:
                action_type = action_event.get("action", "unknown")
                action_counts[action_type] = action_counts.get(action_type, 0) + 1

            context = {
                "admin_action_count": len(admin_actions),
                "time_window_hours": 1,
                "actor": event.actor,
                "user_role": event.user_role,
                "action_breakdown": action_counts,
                "recent_actions": [
                    {
                        "timestamp": hit["timestamp"],
                        "action": hit["action"],
                        "resource": hit["resource"],
                        "event_id": hit["event_id"],
                    }
                    for hit in admin_actions[:10]
                ],
            }

            # Risk score based on count
            risk_score = min(0.9, 0.6 + (len(admin_actions) / 50))
            # Confidence: caps at 0.90, 200 actions → ~0.94 → capped
            confidence = min(0.90, 0.65 + len(admin_actions) / 700)

            return self.create_detection(event, context=context, risk_score=risk_score, confidence=confidence)

        return None

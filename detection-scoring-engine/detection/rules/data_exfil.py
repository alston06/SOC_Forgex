"""Data Exfiltration Detection Rule."""
from typing import Optional

import structlog

from .base import BaseRule
from ..models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity

logger = structlog.get_logger(__name__)


class DataExfilRule(BaseRule):
    """Detect large data exports: >1M bytes export by non-admin user."""

    def __init__(self):
        super().__init__(
            rule_id="data-exfil-001",
            rule_name="Large Data Export",
            rule_description="Non-admin user exporting large amount of data (>1M bytes)",
            severity=DetectionSeverity.CRITICAL,
        )

    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch,  # Not used for this rule (single-event rule)
        normalized_index_prefix,  # Not used for this rule
    ) -> Optional[DetectionEvent]:
        # Check if this is an export action
        if event.action != "export":
            return None

        # Check if user is admin
        if event.user_role == "admin":
            return None

        # Get byte count from extras or normalized_path
        bytes_transferred = None
        if event.extras and "bytes" in event.extras:
            bytes_transferred = event.extras["bytes"]
        elif event.extras and "size" in event.extras:
            bytes_transferred = event.extras["size"]

        if bytes_transferred is None:
            logger.debug("No byte count found for exfil check", event_id=event.event_id)
            return None

        # Check threshold
        threshold = 1_000_000  # 1M bytes

        if bytes_transferred > threshold:
            logger.info(
                "Data exfiltration detected",
                actor=event.actor,
                role=event.user_role,
                bytes=bytes_transferred,
                resource=event.resource,
                event_id=event.event_id,
            )

            context = {
                "bytes_transferred": bytes_transferred,
                "threshold": threshold,
                "actor": event.actor,
                "user_role": event.user_role,
                "resource": event.resource,
                "normalized_path": event.normalized_path,
                "ip": event.ip,
            }

            # Risk score based on bytes transferred
            risk_score = min(1.0, 0.7 + (bytes_transferred / 10_000_000))

            return self.create_detection(event, context=context, risk_score=risk_score)

        return None

"""Rule Engine orchestrator for evaluating detection rules."""
from typing import List, Optional

import structlog
from opensearchpy import OpenSearch

from .rules.base import BaseRule
from .rules.brute_force import BruteForceRule
from .rules.unusual_geo import UnusualGeoRule
from .rules.admin_abuse import AdminAbuseRule
from .rules.data_exfil import DataExfilRule
from .rules.error_storm import ErrorStormRule
from .models import NormalizedActivityEvent, DetectionEvent

logger = structlog.get_logger(__name__)


class RuleEngine:
    """Orchestrates rule evaluation for events."""

    def __init__(self, normalized_index_prefix: str):
        """Initialize rule engine with all rules.

        Args:
            normalized_index_prefix: Prefix for normalized log indices
        """
        self.rules: List[BaseRule] = [
            BruteForceRule(),
            UnusualGeoRule(),
            AdminAbuseRule(),
            DataExfilRule(),
            ErrorStormRule(),
        ]
        self.normalized_index_prefix = normalized_index_prefix

        logger.info(
            "Rule engine initialized",
            rule_count=len(self.rules),
            rules=[r.rule_id for r in self.rules],
        )

    async def evaluate_event(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
    ) -> List[DetectionEvent]:
        """Evaluate event against all rules.

        Args:
            event: Normalized event to evaluate
            opensearch: OpenSearch client for context queries

        Returns:
            List of detections triggered (may be empty or multiple)
        """
        detections = []

        logger.debug(
            "Evaluating event",
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            event_type=event.event_type,
        )

        for rule in self.rules:
            try:
                detection = await rule.evaluate(
                    event,
                    opensearch,
                    self.normalized_index_prefix,
                )

                if detection:
                    detections.append(detection)
                    logger.info(
                        "Rule triggered",
                        rule=rule.rule_id,
                        detection_id=detection.detection_id,
                        event_id=event.event_id,
                    )

            except Exception as e:
                logger.error(
                    "Rule evaluation failed",
                    rule=rule.rule_id,
                    event_id=event.event_id,
                    error=str(e),
                    exc_info=True,
                )

        return detections

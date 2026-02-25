"""Base class for detection rules."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List

import structlog
from opensearchpy import OpenSearch

from ..models import NormalizedActivityEvent, DetectionEvent

logger = structlog.get_logger(__name__)


class BaseRule(ABC):
    """Abstract base class for detection rules."""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_description: str,
        severity: str,
    ):
        """Initialize rule with metadata."""
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_description = rule_description
        self.severity = severity

    @abstractmethod
    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
        normalized_index_prefix: str,
    ) -> Optional[DetectionEvent]:
        """Evaluate if event triggers this rule.

        Args:
            event: The normalized event to evaluate
            opensearch: OpenSearch client for context queries
            normalized_index_prefix: Prefix for normalized log indices

        Returns:
            DetectionEvent if rule triggers, None otherwise
        """
        pass

    async def query_opensearch(
        self,
        opensearch: OpenSearch,
        index_pattern: str,
        query: Dict[str, Any],
        size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Helper method to query OpenSearch.

        Args:
            opensearch: OpenSearch client
            index_pattern: Index pattern to search
            query: OpenSearch query DSL
            size: Maximum number of results

        Returns:
            List of matching documents
        """
        try:
            response = opensearch.search(
                index=index_pattern,
                body={"query": query, "size": size},
            )
            hits = response.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except Exception as e:
            logger.error(
                "OpenSearch query failed",
                rule=self.rule_id,
                error=str(e),
                index=index_pattern,
            )
            return []

    def create_detection(
        self,
        event: NormalizedActivityEvent,
        context: Optional[Dict[str, Any]] = None,
        risk_score: float = 0.0,
        confidence: Optional[float] = None,
    ) -> DetectionEvent:
        """Create a DetectionEvent from triggering event.

        Args:
            event: The triggering event
            context: Additional context from OS queries
            risk_score: Calculated risk score (0.0–1.0)
            confidence: Confidence in the detection (0.0–1.0); defaults to risk_score

        Returns:
            DetectionEvent instance
        """
        import uuid

        return DetectionEvent(
            detection_id=str(uuid.uuid4()),
            tenant_id=event.tenant_id,
            detection_timestamp=datetime.utcnow(),
            rule_name=self.rule_name,
            rule_id=self.rule_id,
            rule_description=self.rule_description,
            severity=self.severity,
            triggering_event=event,
            context=context or {},
            risk_score=risk_score,
            confidence=confidence if confidence is not None else risk_score,
        )

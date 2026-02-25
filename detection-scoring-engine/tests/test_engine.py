"""Tests for the Rule Engine."""
import pytest

from detection.engine import RuleEngine
from detection.models import NormalizedActivityEvent
from datetime import datetime, timezone


class TestRuleEngine:
    """Tests for RuleEngine."""

    def test_initializes_all_rules(self):
        """Test that engine initializes with all expected rules."""
        engine = RuleEngine("logs-")
        assert len(engine.rules) == 5
        rule_ids = {r.rule_id for r in engine.rules}
        expected_ids = {
            "brute-force-001",
            "unusual-geo-001",
            "admin-abuse-001",
            "data-exfil-001",
            "error-storm-001",
        }
        assert rule_ids == expected_ids

    @pytest.mark.asyncio
    async def test_evaluate_event(self, sample_event, mock_opensearch):
        """Test event evaluation."""
        engine = RuleEngine("logs-")
        detections = await engine.evaluate_event(sample_event, mock_opensearch)
        # Since we're not mocking OS responses, we expect no detections
        # or only single-event rules to trigger
        assert isinstance(detections, list)

    @pytest.mark.asyncio
    async def test_continues_on_rule_failure(self, sample_event, mock_opensearch):
        """Test that engine continues even if one rule fails."""
        # Make the OS client raise an exception
        mock_opensearch.search.side_effect = Exception("OS error")

        engine = RuleEngine("logs-")
        # Should not raise, should return empty list
        detections = await engine.evaluate_event(sample_event, mock_opensearch)
        assert isinstance(detections, list)

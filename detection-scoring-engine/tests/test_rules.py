"""Tests for detection rules."""
import pytest
from datetime import datetime, timedelta, timezone

from detection.models import NormalizedActivityEvent, DetectionSeverity
from detection.rules.brute_force import BruteForceRule
from detection.rules.unusual_geo import UnusualGeoRule
from detection.rules.admin_abuse import AdminAbuseRule
from detection.rules.data_exfil import DataExfilRule
from detection.rules.error_storm import ErrorStormRule


class TestBruteForceRule:
    """Tests for BruteForceRule."""

    @pytest.mark.asyncio
    async def test_skips_non_login_failed_events(self, sample_event, mock_opensearch):
        """Test that rule skips events that aren't failed logins."""
        sample_event.event_type = "auth"
        sample_event.action = "login_success"

        rule = BruteForceRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_detects_brute_force(self, sample_event, mock_opensearch):
        """Test that rule detects brute force patterns."""
        sample_event.event_type = "auth"
        sample_event.action = "login_failed"
        sample_event.actor = "attacker"
        sample_event.ip = "10.0.0.1"

        # Mock OS response with 5 failed logins
        mock_opensearch.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"timestamp": datetime.now(timezone.utc), "event_id": f"evt-{i}"}}
                    for i in range(5)
                ]
            }
        }

        rule = BruteForceRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")

        assert detection is not None
        assert detection.rule_id == "brute-force-001"
        assert detection.severity == DetectionSeverity.HIGH
        assert "failed_login_count" in detection.context


class TestUnusualGeoRule:
    """Tests for UnusualGeoRule."""

    @pytest.mark.asyncio
    async def test_skips_non_login_success_events(self, sample_event, mock_opensearch):
        """Test that rule skips events that aren't successful logins."""
        sample_event.event_type = "auth"
        sample_event.action = "login_failed"

        rule = UnusualGeoRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_detects_unusual_geo(self, sample_event, mock_opensearch):
        """Test that rule detects new geographic locations."""
        sample_event.event_type = "auth"
        sample_event.action = "login_success"
        sample_event.geo_country = "RU"

        # Mock OS response with no previous logins from this country
        mock_opensearch.search.return_value = {
            "aggregations": {
                "countries": {"buckets": [{"key": "US", "doc_count": 100}]}
            }
        }

        rule = UnusualGeoRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")

        assert detection is not None
        assert detection.rule_id == "unusual-geo-001"
        assert detection.severity == DetectionSeverity.MEDIUM
        assert "new_country" in detection.context


class TestDataExfilRule:
    """Tests for DataExfilRule."""

    @pytest.mark.asyncio
    async def test_skips_non_export_events(self, sample_event, mock_opensearch):
        """Test that rule skips events that aren't exports."""
        sample_event.action = "view"

        rule = DataExfilRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_skips_admin_users(self, sample_event, mock_opensearch):
        """Test that rule skips admin users."""
        sample_event.action = "export"
        sample_event.user_role = "admin"
        sample_event.extras = {"bytes": 5_000_000}

        rule = DataExfilRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_detects_large_exports(self, sample_event, mock_opensearch):
        """Test that rule detects large data exports."""
        sample_event.action = "export"
        sample_event.user_role = "user"
        sample_event.extras = {"bytes": 5_000_000}

        rule = DataExfilRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")

        assert detection is not None
        assert detection.rule_id == "data-exfil-001"
        assert detection.severity == DetectionSeverity.CRITICAL
        assert detection.context["bytes_transferred"] == 5_000_000


class TestAdminAbuseRule:
    """Tests for AdminAbuseRule."""

    @pytest.mark.asyncio
    async def test_skips_non_admin_actions(self, sample_event, mock_opensearch):
        """Test that rule skips non-admin actions."""
        sample_event.action = "view"

        rule = AdminAbuseRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_skips_admin_users(self, sample_event, mock_opensearch):
        """Test that rule skips admin users."""
        sample_event.action = "user_delete"
        sample_event.user_role = "admin"

        rule = AdminAbuseRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_detects_admin_abuse(self, sample_event, mock_opensearch):
        """Test that rule detects admin abuse."""
        sample_event.action = "user_delete"
        sample_event.user_role = "user"

        # Mock OS response with 10 admin actions
        from datetime import datetime, timezone
        mock_opensearch.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"action": "user_delete", "event_id": f"evt-{i}", "timestamp": datetime.now(timezone.utc).isoformat(), "resource": "/api/users"}}
                    for i in range(10)
                ]
            }
        }

        rule = AdminAbuseRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")

        assert detection is not None
        assert detection.rule_id == "admin-abuse-001"
        assert detection.severity == DetectionSeverity.HIGH
        assert detection.context["admin_action_count"] == 10


class TestErrorStormRule:
    """Tests for ErrorStormRule."""

    @pytest.mark.asyncio
    async def test_skips_non_http_events(self, sample_event, mock_opensearch):
        """Test that rule skips non-HTTP events."""
        sample_event.event_type = "auth"

        rule = ErrorStormRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_skips_non_5xx_errors(self, sample_event, mock_opensearch):
        """Test that rule skips non-5xx status codes."""
        sample_event.event_type = "http"
        sample_event.extras = {"status_code": 200}

        rule = ErrorStormRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")
        assert detection is None

    @pytest.mark.asyncio
    async def test_detects_error_storm(self, sample_event, mock_opensearch):
        """Test that rule detects error storms."""
        sample_event.event_type = "http"
        sample_event.extras = {"status_code": 500}
        sample_event.ip = "10.0.0.1"
        sample_event.normalized_path = "/api/data"

        # Mock OS response with 50 errors
        mock_opensearch.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "timestamp": datetime.now(timezone.utc),
                            "event_id": f"evt-{i}",
                        }
                    }
                    for i in range(50)
                ]
            }
        }

        rule = ErrorStormRule()
        detection = await rule.evaluate(sample_event, mock_opensearch, "logs-")

        assert detection is not None
        assert detection.rule_id == "error-storm-001"
        assert detection.severity == DetectionSeverity.MEDIUM
        assert detection.context["error_count"] == 50

"""Tests for the Alerts API."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from detection.app import app


class TestAlertsAPI:
    """Tests for the alerts API endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        client = TestClient(app)
        # Initialize the opensearch attribute for tests
        client.app.state.opensearch = MagicMock()
        return client

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_alerts_requires_tenant_id(self, client):
        """Test that tenant_id is required."""
        response = client.get("/v1/alerts")
        assert response.status_code == 422  # Validation error

    def test_alerts_with_tenant_id(self, client):
        """Test alerts endpoint with tenant_id."""
        client.app.state.opensearch.search.return_value = {"hits": {"hits": []}}

        with patch("detection.api.alerts._indices_for_range") as mock_indices:
            mock_indices.return_value = ["detections-tenant-001-2026-02"]

            response = client.get("/v1/alerts?tenant_id=tenant-001")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_alerts_limit_enforced(self, client):
        """Test that limit parameter is enforced."""
        client.app.state.opensearch.search.return_value = {"hits": {"hits": []}}

        with patch("detection.api.alerts._indices_for_range") as mock_indices:
            mock_indices.return_value = ["detections-tenant-001-2026-02"]

            # Test max limit
            response = client.get("/v1/alerts?tenant_id=tenant-001&limit=300")
            assert response.status_code == 422  # Validation error for limit > 200

            # Test valid limit
            response = client.get("/v1/alerts?tenant_id=tenant-001&limit=50")
            assert response.status_code == 200

    def test_invalid_since_format(self, client):
        """Test that invalid since format returns error."""
        client.app.state.opensearch.search.return_value = {"hits": {"hits": []}}

        with patch("detection.api.alerts._indices_for_range") as mock_indices:
            mock_indices.return_value = ["detections-tenant-001-2026-02"]

            response = client.get("/v1/alerts?tenant_id=tenant-001&since=invalid")
            assert response.status_code == 400

    def test_alerts_filters(self, client):
        """Test filtering by rule_id and severity."""
        # Need to provide a complete detection event in the mock
        from datetime import datetime, timezone
        from detection.models import NormalizedActivityEvent
        sample_event = NormalizedActivityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="auth",
            actor="user123",
            resource="/api/login",
            action="login_success",
            tenant_id="tenant-001",
            event_id="test-001",
            normalized_path="/api/login",
            extras={}
        )
        mock_detection = {
            "detection_id": "det-001",
            "tenant_id": "tenant-001",
            "detection_timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_name": "Test Rule",
            "rule_id": "brute-force-001",
            "rule_description": "Test",
            "severity": "high",
            "status": "open",
            "triggering_event": sample_event.model_dump(),
            "context": {},
            "risk_score": 0.8,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        client.app.state.opensearch.search.return_value = {
            "hits": {"hits": [{"_source": mock_detection}]}
        }

        with patch("detection.api.alerts._indices_for_range") as mock_indices:
            mock_indices.return_value = ["detections-tenant-001-2026-02"]

            response = client.get("/v1/alerts?tenant_id=tenant-001&rule_id=brute-force-001&severity=high")
            assert response.status_code == 200

            # Verify the OS query included the filters
            call_args = client.app.state.opensearch.search.call_args
            if call_args:
                query = call_args[1]["body"]["query"]
                must = query["bool"]["must"]
                # Check if any term query contains rule_id or severity
                has_rule_id = any(
                    "term" in item and "rule_id" in item.get("term", {})
                    for item in must
                )
                has_severity = any(
                    "term" in item and "severity" in item.get("term", {})
                    for item in must
                )
                assert has_rule_id
                assert has_severity

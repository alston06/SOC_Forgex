"""Pytest fixtures for detection tests."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from detection.models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity


@pytest.fixture
def sample_event():
    """Sample normalized activity event for testing."""
    return NormalizedActivityEvent(
        timestamp=datetime.now(timezone.utc),
        event_type="auth",
        actor="user123",
        resource="/api/auth/login",
        action="login_success",
        ip="192.168.1.1",
        service_name="auth-service",
        environment="production",
        tenant_id="tenant-001",
        geo_country="US",
        geo_city="San Francisco",
        user_role="user",
        normalized_path="/api/auth/login",
        risk_score=0.0,
        event_id="test-event-001",
        extras={},
    )


@pytest.fixture
def mock_opensearch():
    """Mock OpenSearch client."""
    return MagicMock()


@pytest.fixture
def sample_detection(sample_event):
    """Sample detection event for testing."""
    return DetectionEvent(
        detection_id="test-detection-001",
        tenant_id="tenant-001",
        detection_timestamp=datetime.now(timezone.utc),
        rule_name="Test Rule",
        rule_id="test-rule-001",
        rule_description="Test rule description",
        severity=DetectionSeverity.HIGH,
        triggering_event=sample_event,
        risk_score=0.8,
    )

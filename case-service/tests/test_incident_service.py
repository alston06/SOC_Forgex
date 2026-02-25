import pytest
from datetime import datetime
from app.services.incident_service import open_incident, update_incident, close_incident
from unittest.mock import Mock
from app.models.internal_case_action import CaseActionRequest


def test_open_incident(mock_mongo):
    """Test opening a new incident."""
    data = Mock(
        tenant_id="tenant-123",
        detection_id="det-001",
        severity="HIGH",
        summary="Test incident"
    )

    case_id = open_incident(data)

    # Verify case_id is returned
    assert case_id is not None
    assert isinstance(case_id, str)

    # Verify incident was saved to database
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident is not None
    assert incident["tenant_id"] == "tenant-123"
    assert incident["detection_id"] == "det-001"
    assert incident["status"] == "OPEN"
    assert incident["severity"] == "HIGH"
    assert incident["agent_summary"]["initial_summary"] == "Test incident"
    assert isinstance(incident["created_at"], datetime)
    assert isinstance(incident["updated_at"], datetime)


def test_update_incident_severity(mock_mongo, test_incident):
    """Test updating an incident's severity."""
    case_id = test_incident["_id"]
    update_incident(case_id, severity="CRITICAL")

    # Verify incident was updated
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["severity"] == "CRITICAL"


def test_update_incident_no_severity(mock_mongo, test_incident):
    """Test updating an incident without changing severity."""
    case_id = test_incident["_id"]
    original_severity = test_incident["severity"]

    update_incident(case_id)

    # Verify severity stayed the same and updated_at was updated
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["severity"] == original_severity
    assert "updated_at" in incident


def test_close_incident(mock_mongo, test_incident):
    """Test closing an incident."""
    case_id = test_incident["_id"]
    close_incident(case_id)

    # Verify incident was closed
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["status"] == "RESOLVED"
    assert isinstance(incident["updated_at"], datetime)


def test_open_incident_multiple(mock_mongo):
    """Test opening multiple incidents for the same tenant."""
    data1 = Mock(
        tenant_id="tenant-123",
        detection_id="det-001",
        severity="HIGH",
        summary="Incident 1"
    )
    data2 = Mock(
        tenant_id="tenant-123",
        detection_id="det-002",
        severity="MEDIUM",
        summary="Incident 2"
    )

    case_id_1 = open_incident(data1)
    case_id_2 = open_incident(data2)

    # Verify both incidents were created with different IDs
    assert case_id_1 != case_id_2

    # Verify both incidents exist in database
    incidents = list(mock_mongo.incidents.find({"tenant_id": "tenant-123"}))
    assert len(incidents) == 2

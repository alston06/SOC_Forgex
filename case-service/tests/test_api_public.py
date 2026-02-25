import pytest
from datetime import datetime
from unittest.mock import patch, Mock


def test_list_incidents(client, mock_mongo, test_api_key, test_tenant_id):
    """Test listing incidents."""
    # Create some test incidents
    mock_mongo.incidents.insert_many([
        {
            "_id": "case-001",
            "tenant_id": test_tenant_id,
            "status": "OPEN",
            "severity": "HIGH",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "case-002",
            "tenant_id": test_tenant_id,
            "status": "OPEN",
            "severity": "MEDIUM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "case-003",
            "tenant_id": "other-tenant",
            "status": "OPEN",
            "severity": "LOW",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ])

    response = client.get(
        "/v1/incidents",
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 2  # Only tenant's incidents
    assert all("id" in i for i in incidents)
    assert all(i["status"] == "OPEN" for i in incidents)
    assert all(i.get("severity") for i in incidents)


def test_list_incidents_with_status_filter(client, mock_mongo, test_api_key, test_tenant_id):
    """Test listing incidents with status filter."""
    mock_mongo.incidents.insert_many([
        {
            "_id": "case-001",
            "tenant_id": test_tenant_id,
            "status": "OPEN",
            "severity": "HIGH",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "_id": "case-002",
            "tenant_id": test_tenant_id,
            "status": "RESOLVED",
            "severity": "MEDIUM",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ])

    response = client.get(
        "/v1/incidents?status=RESOLVED",
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 1
    assert incidents[0]["id"] == "case-002"
    assert incidents[0]["status"] == "RESOLVED"


def test_list_incidents_empty(client, test_api_key):
    """Test listing incidents when none exist."""
    response = client.get(
        "/v1/incidents",
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 0


def test_list_incidents_unauthorized(client):
    """Test unauthorized access to incidents list."""
    response = client.get(
        "/v1/incidents",
        headers={"X-API-Key": "invalid-key"}
    )

    assert response.status_code == 401


def test_get_incident(client, mock_mongo, test_incident, test_api_key):
    """Test getting a single incident."""
    case_id = test_incident["_id"]

    response = client.get(
        f"/v1/incidents/{case_id}",
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    data = response.json()
    assert "incident" in data
    assert "detection" in data
    assert "logs" in data
    assert data["incident"]["id"] == case_id


def test_get_incident_not_found(client, test_api_key):
    """Test getting a non-existent incident."""
    response = client.get(
        "/v1/incidents/nonexistent-case",
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 404


def test_get_incident_unauthorized(client):
    """Test unauthorized access to get incident."""
    response = client.get(
        "/v1/incidents/case-001",
        headers={"X-API-Key": "invalid-key"}
    )

    assert response.status_code == 401


def test_update_incident_notes(client, mock_mongo, test_incident, test_api_key):
    """Test updating incident notes."""
    case_id = test_incident["_id"]

    response = client.post(
        f"/v1/incidents/{case_id}/notes",
        json={"notes": "Updated notes from analyst"},
        headers={"X-API-Key": test_api_key}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the notes were updated
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["human_notes"] == "Updated notes from analyst"


def test_update_incident_notes_unauthorized(client):
    """Test unauthorized access to update notes."""
    response = client.post(
        "/v1/incidents/case-001/notes",
        json={"notes": "test notes"},
        headers={"X-API-Key": "invalid-key"}
    )

    assert response.status_code == 401

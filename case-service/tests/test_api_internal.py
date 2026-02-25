import pytest
from unittest.mock import patch, Mock


def test_case_action_open(client, test_api_key, internal_token):
    """Test opening a case via internal API."""
    with patch('app.api.internal.case_actions.send_incident_open_webhooks'):
        response = client.post(
            "/internal/case-action",
            json={
                "action": "open",
                "tenant_id": "tenant-123",
                "detection_id": "det-001",
                "severity": "HIGH",
                "summary": "Test incident"
            },
            headers={
                "Authorization": f"Bearer {internal_token}"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
    assert data["status"] == "created"


def test_case_action_update(client, mock_mongo, test_incident, internal_token):
    """Test updating a case via internal API."""
    case_id = test_incident["_id"]

    response = client.post(
        "/internal/case-action",
        json={
            "action": "update",
            "tenant_id": test_incident["tenant_id"],
            "detection_id": test_incident["detection_id"],
            "case_id": case_id,
            "severity": "CRITICAL"
        },
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["status"] == "updated"

    # Verify the update in database
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["severity"] == "CRITICAL"


def test_case_action_close(client, mock_mongo, test_incident, internal_token):
    """Test closing a case via internal API."""
    case_id = test_incident["_id"]

    response = client.post(
        "/internal/case-action",
        json={
            "action": "close",
            "tenant_id": test_incident["tenant_id"],
            "detection_id": test_incident["detection_id"],
            "case_id": case_id
        },
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["status"] == "resolved"

    # Verify the close in database
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert incident["status"] == "RESOLVED"


def test_case_action_invalid(client, internal_token):
    """Test invalid case action."""
    response = client.post(
        "/internal/case-action",
        json={
            "action": "invalid",
            "tenant_id": "tenant-123",
            "detection_id": "det-001"
        },
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data.get("error") == "Invalid action"


def test_case_action_unauthorized(client, test_api_key):
    """Test unauthorized access to case action."""
    response = client.post(
        "/internal/case-action",
        json={
            "action": "open",
            "tenant_id": "tenant-123",
            "detection_id": "det-001",
            "severity": "HIGH",
            "summary": "Test incident"
        },
        headers={
            "Authorization": "Bearer invalid-token"
        }
    )

    assert response.status_code == 401


def test_agent_output(client, mock_mongo, test_incident, internal_token):
    """Test receiving agent output."""
    case_id = test_incident["_id"]

    response = client.post(
        "/internal/agent-output",
        json={
            "case_id": case_id,
            "agent_type": "triage",
            "output": {"analysis": "This is a triage analysis", "confidence": 0.9}
        },
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the output was saved
    incident = mock_mongo.incidents.find_one({"_id": case_id})
    assert "triage" in incident["agent_summary"]
    assert incident["agent_summary"]["triage"]["analysis"] == "This is a triage analysis"


def test_agent_output_unauthorized(client):
    """Test unauthorized access to agent output."""
    response = client.post(
        "/internal/agent-output",
        json={
            "case_id": "case-001",
            "agent_type": "triage",
            "output": {"analysis": "test"}
        },
        headers={
            "Authorization": "Bearer invalid-token"
        }
    )

    assert response.status_code == 401


def test_get_incident_detail(client, mock_mongo, test_incident, internal_token):
    """Test getting incident detail."""
    case_id = test_incident["_id"]

    response = client.get(
        f"/internal/incident/{case_id}",
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "incident" in data
    assert "detection" in data
    assert "logs" in data
    assert data["incident"]["id"] == case_id


def test_get_incident_detail_not_found(client, internal_token):
    """Test getting a non-existent incident."""
    response = client.get(
        "/internal/incident/nonexistent-case",
        headers={
            "Authorization": f"Bearer {internal_token}"
        }
    )

    assert response.status_code == 404


def test_get_incident_detail_unauthorized(client):
    """Test unauthorized access to incident detail."""
    response = client.get(
        "/internal/incident/case-001",
        headers={
            "Authorization": "Bearer invalid-token"
        }
    )

    assert response.status_code == 401

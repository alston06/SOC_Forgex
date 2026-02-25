import pytest
from fastapi.testclient import TestClient
from mongomock import MongoClient
from unittest.mock import patch
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.mongo import db
from app.core.config import settings


@pytest.fixture
def mock_mongo():
    """Create a mock MongoDB client for testing."""
    client = MongoClient()
    mock_db = client["test_soc_db"]

    # Patch the db module to use the mock
    with patch.object(db, "__setattr__", lambda _, name, value: None):
        # Directly replace the db object's attributes
        original_incidents = db.incidents
        original_api_keys = db.api_keys

        db.incidents = mock_db["incidents"]
        db.api_keys = mock_db["api_keys"]

        yield db

        # Restore original
        db.incidents = original_incidents
        db.api_keys = original_api_keys


@pytest.fixture
def client(mock_mongo):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_tenant_id():
    """A test tenant ID."""
    return "tenant-123"


@pytest.fixture
def test_api_key(mock_mongo, test_tenant_id):
    """Create a test API key in the database."""
    import hashlib
    api_key = "test-api-key-12345"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    mock_mongo.api_keys.insert_one({
        "key_hash": key_hash,
        "tenant_id": test_tenant_id
    })

    return api_key


@pytest.fixture
def test_incident(mock_mongo, test_tenant_id):
    """Create a test incident in the database."""
    from datetime import datetime

    incident_data = {
        "_id": "case-001",
        "tenant_id": test_tenant_id,
        "detection_id": "det-001",
        "status": "OPEN",
        "severity": "HIGH",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "assigned_to": None,
        "agent_summary": {
            "initial_summary": "Test incident summary"
        },
        "human_notes": ""
    }

    mock_mongo.incidents.insert_one(incident_data)
    return incident_data


@pytest.fixture
def internal_token():
    """Return the internal token for testing."""
    return settings.INTERNAL_TOKEN

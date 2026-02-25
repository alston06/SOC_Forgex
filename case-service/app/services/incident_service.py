from datetime import datetime
from uuid import uuid4
from app.db.mongo import db


def open_incident(data):
    case_id = str(uuid4())

    incident = {
        "_id": case_id,
        "tenant_id": data.tenant_id,
        "detection_id": data.detection_id,
        "status": "OPEN",
        "severity": data.severity,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "assigned_to": None,
        "agent_summary": {
            "initial_summary": data.summary
        },
        "human_notes": ""
    }

    db.incidents.insert_one(incident)
    return case_id


def update_incident(case_id, severity=None):
    update_fields = {"updated_at": datetime.utcnow()}
    if severity:
        update_fields["severity"] = severity

    db.incidents.update_one(
        {"_id": case_id},
        {"$set": update_fields}
    )


def close_incident(case_id):
    db.incidents.update_one(
        {"_id": case_id},
        {
            "$set": {
                "status": "RESOLVED",
                "updated_at": datetime.utcnow()
            }
        }
    )
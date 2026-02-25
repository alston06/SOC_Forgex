import requests
from datetime import datetime
from app.db.mongo import db


def send_incident_open_webhooks(tenant_id, case_id, severity):
    webhooks = db.tenant_webhooks.find({
        "tenant_id": tenant_id,
        "events": "incident_open",
        "active": True
    })

    for webhook in webhooks:
        payload = {
            "event": "incident_open",
            "tenant_id": tenant_id,
            "incident_id": case_id,
            "severity": severity
        }

        try:
            requests.post(webhook["url"], json=payload, timeout=5)
            status = "SENT"
        except Exception:
            status = "FAILED"

        db.notifications.insert_one({
            "incident_id": case_id,
            "channel": "webhook",
            "target": webhook["url"],
            "status": status,
            "payload": payload,
            "sent_at": datetime.utcnow()
        })
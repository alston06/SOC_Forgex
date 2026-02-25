from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import resolve_tenant
from app.db.mongo import db
from datetime import datetime
from app.core.config import settings
import requests

router = APIRouter()


@router.get("/v1/incidents")
def list_incidents(status: str = "OPEN", tenant_id: str = Depends(resolve_tenant)):

    incidents = list(db.incidents.find(
        {"tenant_id": tenant_id, "status": status},
        {"_id": 1, "status": 1, "severity": 1, "created_at": 1}
    ))

    for i in incidents:
        i["id"] = str(i.pop("_id"))

    return incidents


@router.get("/v1/incidents/{id}")
def get_incident(id: str, tenant_id: str = Depends(resolve_tenant)):
    incident = db.incidents.find_one({"_id": id, "tenant_id": tenant_id})
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")

    incident_resp = dict(incident)
    incident_resp["id"] = str(incident_resp.pop("_id"))

    detection = None
    logs = []

    # fetch detection from detection service (best-effort)
    try:
        detection_url = f"http://detection-service:8005/v1/alerts"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        params = {"tenant_id": tenant_id, "limit": 50}
        resp = requests.get(detection_url, params=params, headers=headers, timeout=3)
        if resp.status_code == 200:
            alerts = resp.json()
            for a in alerts:
                if a.get("detection_id") == incident.get("detection_id"):
                    detection = a
                    break
    except Exception:
        detection = None

    # fetch logs via normalizer (best-effort)
    try:
        normalizer_url = "http://normalizer:8001/internal/query-logs"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        payload = {
            "tenant_id": tenant_id,
            "query": {},
            "time_from": None,
            "time_to": None,
            "limit": 100,
        }

        if detection and detection.get("entities"):
            actor_list = detection.get("entities", {}).get("actor")
            if actor_list:
                payload["query"] = {"actor": actor_list[0]}

        resp = requests.post(normalizer_url, json=payload, headers=headers, timeout=4)
        if resp.status_code == 200:
            logs = resp.json().get("events", [])
    except Exception:
        logs = []

    return {"incident": incident_resp, "detection": detection, "logs": logs}


@router.post("/v1/incidents/{id}/notes")
def update_incident_notes(id: str, body: dict = Body(...), tenant_id: str = Depends(resolve_tenant)):
    notes = body.get("notes", "")
    db.incidents.update_one({"_id": id, "tenant_id": tenant_id}, {"$set": {"human_notes": notes, "updated_at": datetime.utcnow()}})
    return {"status": "ok"}
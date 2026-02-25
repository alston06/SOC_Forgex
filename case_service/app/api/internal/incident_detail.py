from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_internal_token
from app.db.mongo import db
from app.core.config import settings
import requests

router = APIRouter()


@router.get("/internal/incident/{case_id}", dependencies=[Depends(verify_internal_token)])
def get_incident_detail(case_id: str):
    incident = db.incidents.find_one({"_id": case_id})
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")

    # normalize response id
    incident_resp = dict(incident)
    incident_resp["id"] = incident_resp.pop("_id")

    detection = None
    logs = []

    # Try fetch detection from detection service (best-effort)
    try:
        detection_url = f"http://detection-service:8005/v1/alerts"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        params = {"tenant_id": incident.get("tenant_id"), "limit": 50}
        resp = requests.get(detection_url, params=params, headers=headers, timeout=3)
        if resp.status_code == 200:
            alerts = resp.json()
            # alerts expected as list of DetectionEvent objects
            for a in alerts:
                if a.get("detection_id") == incident.get("detection_id"):
                    detection = a
                    break
    except Exception:
        detection = None

    # Try fetch related logs from normalizer (best-effort)
    try:
        normalizer_url = "http://normalizer:8001/internal/query-logs"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        payload = {
            "tenant_id": incident.get("tenant_id"),
            "query": {},
            "time_from": None,
            "time_to": None,
            "limit": 100,
        }

        # if detection has useful entities, prefer searching by actor
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

from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.dashboard_auth import get_current_user
from app.models.dashboard import UpdateIncidentStatusRequest, UpdateIncidentNotesRequest
from app.db.mongo import db
from app.core.config import settings
from datetime import datetime
import requests as http_requests

router = APIRouter(prefix="/dashboard/incidents", tags=["Dashboard Incidents"])


@router.get("")
def list_incidents(
    status: str = Query(None),
    severity: str = Query(None),
    limit: int = Query(50, le=500),
    user: dict = Depends(get_current_user),
):
    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity

    incidents = list(
        db.incidents.find(query).sort("created_at", -1).limit(limit)
    )

    for i in incidents:
        i["id"] = str(i.pop("_id"))
        if isinstance(i.get("created_at"), datetime):
            i["created_at"] = i["created_at"].isoformat()
        if isinstance(i.get("updated_at"), datetime):
            i["updated_at"] = i["updated_at"].isoformat()
        # Extract initial summary for list view
        agent_summary = i.get("agent_summary", {})
        i["summary"] = agent_summary.get("initial_summary", "")

    return incidents


@router.get("/{incident_id}")
def get_incident(incident_id: str, user: dict = Depends(get_current_user)):
    incident = db.incidents.find_one(
        {"_id": incident_id, "tenant_id": user["tenant_id"]}
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident_resp = dict(incident)
    incident_resp["id"] = str(incident_resp.pop("_id"))

    for field in ["created_at", "updated_at"]:
        if isinstance(incident_resp.get(field), datetime):
            incident_resp[field] = incident_resp[field].isoformat()

    detection = None
    logs = []

    # Fetch detection from detection service (best-effort)
    try:
        detection_url = f"{settings.DETECTION_SERVICE_URL}/v1/alerts"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        params = {"tenant_id": user["tenant_id"], "limit": 50}
        resp = http_requests.get(
            detection_url, params=params, headers=headers, timeout=3
        )
        if resp.status_code == 200:
            alerts = resp.json()
            for a in alerts:
                if a.get("detection_id") == incident.get("detection_id"):
                    detection = a
                    break
    except Exception:
        detection = None

    # Fetch related logs from normalizer (best-effort)
    try:
        normalizer_url = f"{settings.NORMALIZER_SERVICE_URL}/internal/query-logs"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        payload = {
            "tenant_id": user["tenant_id"],
            "query": {},
            "time_from": None,
            "time_to": None,
            "limit": 100,
        }
        if detection and detection.get("entities"):
            actor_list = detection.get("entities", {}).get("actor")
            if actor_list:
                payload["query"] = {"actor": actor_list[0]}
        resp = http_requests.post(
            normalizer_url, json=payload, headers=headers, timeout=4
        )
        if resp.status_code == 200:
            logs = resp.json().get("events", [])
    except Exception:
        logs = []

    return {"incident": incident_resp, "detection": detection, "logs": logs}


@router.post("/{incident_id}/status")
def update_status(
    incident_id: str,
    data: UpdateIncidentStatusRequest,
    user: dict = Depends(get_current_user),
):
    valid_statuses = ["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )
    result = db.incidents.update_one(
        {"_id": incident_id, "tenant_id": user["tenant_id"]},
        {"$set": {"status": data.status, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "updated"}


@router.post("/{incident_id}/notes")
def update_notes(
    incident_id: str,
    data: UpdateIncidentNotesRequest,
    user: dict = Depends(get_current_user),
):
    result = db.incidents.update_one(
        {"_id": incident_id, "tenant_id": user["tenant_id"]},
        {"$set": {"human_notes": data.notes, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "updated"}

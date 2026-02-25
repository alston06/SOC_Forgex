from fastapi import APIRouter, Depends
from app.core.security import verify_internal_token
from app.models.internal_case_action import CaseActionRequest
from app.services.incident_service import open_incident, update_incident, close_incident
from app.services.notification_service import send_incident_open_webhooks

router = APIRouter()


@router.post("/internal/case-action", dependencies=[Depends(verify_internal_token)])
def case_action(data: CaseActionRequest):

    if data.action == "open":
        case_id = open_incident(data)
        send_incident_open_webhooks(data.tenant_id, case_id, data.severity)
        return {"case_id": case_id, "status": "created"}

    elif data.action == "update":
        update_incident(data.case_id, data.severity)
        return {"case_id": data.case_id, "status": "updated"}

    elif data.action == "close":
        close_incident(data.case_id)
        return {"case_id": data.case_id, "status": "resolved"}

    return {"error": "Invalid action"}
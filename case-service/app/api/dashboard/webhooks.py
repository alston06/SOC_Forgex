from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.dashboard_auth import get_current_user
from app.db.mongo import db
from datetime import datetime

router = APIRouter(prefix="/dashboard/webhooks", tags=["Dashboard Webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str]


@router.get("")
def list_webhooks(user: dict = Depends(get_current_user)):
    webhooks = list(db.tenant_webhooks.find({"tenant_id": user["tenant_id"]}))
    for w in webhooks:
        w["id"] = str(w.pop("_id"))
        if isinstance(w.get("created_at"), datetime):
            w["created_at"] = w["created_at"].isoformat()
    return webhooks


@router.post("")
def create_webhook(
    data: WebhookCreateRequest, user: dict = Depends(get_current_user)
):
    doc = {
        "tenant_id": user["tenant_id"],
        "events": data.events,
        "url": data.url,
        "active": True,
        "created_at": datetime.utcnow(),
    }
    db.tenant_webhooks.insert_one(doc)
    return {"status": "created"}


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str, user: dict = Depends(get_current_user)):
    from bson import ObjectId

    try:
        result = db.tenant_webhooks.delete_one(
            {"_id": ObjectId(webhook_id), "tenant_id": user["tenant_id"]}
        )
    except Exception:
        result = db.tenant_webhooks.delete_one(
            {"_id": webhook_id, "tenant_id": user["tenant_id"]}
        )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted"}

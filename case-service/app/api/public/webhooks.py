from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from app.core.security import resolve_tenant
from app.db.mongo import db
from datetime import datetime

router = APIRouter()


class WebhookRequest(BaseModel):
    url: HttpUrl
    events: list[str]


@router.post("/v1/webhooks")
def create_or_update_webhook(data: WebhookRequest, tenant_id: str = Depends(resolve_tenant)):
    doc = {
        "tenant_id": tenant_id,
        "events": data.events,
        "url": str(data.url),
        "active": True,
        "created_at": datetime.utcnow()
    }

    existing = db.tenant_webhooks.find_one({"tenant_id": tenant_id, "url": str(data.url)})
    if existing:
        db.tenant_webhooks.update_one({"_id": existing["_id"]}, {"$set": doc})
    else:
        db.tenant_webhooks.insert_one(doc)

    return {"status": "ok"}


@router.get("/v1/webhooks")
def list_webhooks(tenant_id: str = Depends(resolve_tenant)):
    webhooks = list(db.tenant_webhooks.find({"tenant_id": tenant_id}))
    for w in webhooks:
        w["id"] = str(w.pop("_id"))
    return webhooks

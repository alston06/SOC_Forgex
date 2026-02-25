from fastapi import APIRouter, Depends
from app.core.dashboard_auth import get_current_user
from app.db.mongo import db
from datetime import datetime

router = APIRouter(prefix="/dashboard/stats", tags=["Dashboard Stats"])


@router.get("")
def get_stats(user: dict = Depends(get_current_user)):
    tenant_id = user["tenant_id"]

    # Count incidents by status
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_counts = {
        doc["_id"]: doc["count"] for doc in db.incidents.aggregate(pipeline)
    }

    # Count incidents by severity (non-resolved only)
    severity_pipeline = [
        {"$match": {"tenant_id": tenant_id, "status": {"$ne": "RESOLVED"}}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
    ]
    severity_counts = {
        doc["_id"]: doc["count"]
        for doc in db.incidents.aggregate(severity_pipeline)
    }

    total = sum(status_counts.values())
    open_count = status_counts.get("OPEN", 0)
    investigating = status_counts.get("INVESTIGATING", 0)
    contained = status_counts.get("CONTAINED", 0)
    resolved = status_counts.get("RESOLVED", 0)

    # Recent incidents (last 10)
    recent = list(
        db.incidents.find({"tenant_id": tenant_id})
        .sort("created_at", -1)
        .limit(10)
    )
    for i in recent:
        i["id"] = str(i.pop("_id"))
        if isinstance(i.get("created_at"), datetime):
            i["created_at"] = i["created_at"].isoformat()
        if isinstance(i.get("updated_at"), datetime):
            i["updated_at"] = i["updated_at"].isoformat()
        agent_summary = i.get("agent_summary", {})
        i["summary"] = agent_summary.get("initial_summary", "")

    # API keys count
    api_keys_count = db.api_keys.count_documents(
        {"tenant_id": tenant_id, "active": {"$ne": False}}
    )

    # Webhooks count
    webhooks_count = db.tenant_webhooks.count_documents(
        {"tenant_id": tenant_id, "active": True}
    )

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "investigating_incidents": investigating,
        "contained_incidents": contained,
        "resolved_incidents": resolved,
        "severity_breakdown": severity_counts,
        "recent_incidents": recent,
        "api_keys_count": api_keys_count,
        "webhooks_count": webhooks_count,
    }

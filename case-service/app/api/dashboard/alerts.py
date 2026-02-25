from fastapi import APIRouter, Depends, Query
from app.core.dashboard_auth import get_current_user
from app.core.config import settings
import requests as http_requests
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard/alerts", tags=["Dashboard Alerts"])


@router.get("")
def get_alerts(
    limit: int = Query(100, le=500),
    since: str = Query(None),
    user: dict = Depends(get_current_user),
):
    try:
        if not since:
            since = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"

        detection_url = f"{settings.DETECTION_SERVICE_URL}/v1/alerts"
        headers = {"Authorization": f"Bearer {settings.INTERNAL_TOKEN}"}
        params = {
            "tenant_id": user["tenant_id"],
            "limit": limit,
            "since": since,
        }
        resp = http_requests.get(
            detection_url, params=params, headers=headers, timeout=10
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []

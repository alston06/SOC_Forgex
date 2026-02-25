from fastapi import APIRouter, HTTPException, Depends
from app.core.dashboard_auth import get_current_user
from app.models.dashboard import APIKeyCreateRequest
from app.services.api_key_service import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/dashboard/api-keys", tags=["Dashboard API Keys"])


@router.get("")
def list_keys(user: dict = Depends(get_current_user)):
    return list_api_keys(user["tenant_id"])


@router.post("")
def create_key(data: APIKeyCreateRequest, user: dict = Depends(get_current_user)):
    return create_api_key(user["tenant_id"], data.name, user["user_id"])


@router.delete("/{key_id}")
def revoke_key(key_id: str, user: dict = Depends(get_current_user)):
    success = revoke_api_key(user["tenant_id"], key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "revoked"}

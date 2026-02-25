from fastapi import Header, HTTPException, Depends
from app.core.config import settings
import hashlib
from datetime import datetime
from app.db.mongo import db


def verify_internal_token(authorization: str = Header(...)):
    if authorization != f"Bearer {settings.INTERNAL_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid internal token")


def resolve_tenant(api_key: str = Header(..., alias="X-API-Key")):
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    record = db.api_keys.find_one({"key_hash": key_hash, "active": {"$ne": False}})
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API key")
    db.api_keys.update_one(
        {"_id": record["_id"]}, {"$set": {"last_used_at": datetime.utcnow()}}
    )
    return record["tenant_id"]
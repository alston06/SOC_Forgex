import hashlib
import secrets
from datetime import datetime
from uuid import uuid4
from app.db.mongo import db


def create_api_key(tenant_id: str, name: str, created_by: str) -> dict:
    """Create a new API key. Returns the raw key (shown only once)."""
    raw_key = f"sfx_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:12]

    key_id = str(uuid4())
    doc = {
        "_id": key_id,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
        "name": name,
        "tenant_id": tenant_id,
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "last_used_at": None,
        "active": True,
    }

    db.api_keys.insert_one(doc)

    return {
        "id": key_id,
        "name": name,
        "key": raw_key,
        "prefix": key_prefix,
        "created_at": doc["created_at"].isoformat(),
    }


def list_api_keys(tenant_id: str) -> list:
    """List all API keys for a tenant (without the actual key)."""
    keys = list(db.api_keys.find({"tenant_id": tenant_id}))
    result = []
    for key in keys:
        result.append(
            {
                "id": key["_id"],
                "name": key.get("name", key.get("service_name", "Unnamed Key")),
                "prefix": key.get("key_prefix", "***"),
                "active": key.get("active", True),
                "created_at": (
                    key["created_at"].isoformat()
                    if isinstance(key.get("created_at"), datetime)
                    else str(key.get("created_at", ""))
                ),
                "last_used_at": (
                    key["last_used_at"].isoformat()
                    if isinstance(key.get("last_used_at"), datetime)
                    else None
                ),
            }
        )
    return result


def revoke_api_key(tenant_id: str, key_id: str) -> bool:
    """Revoke an API key."""
    result = db.api_keys.update_one(
        {"_id": key_id, "tenant_id": tenant_id}, {"$set": {"active": False}}
    )
    return result.modified_count > 0

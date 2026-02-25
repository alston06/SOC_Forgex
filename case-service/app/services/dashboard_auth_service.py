import bcrypt
from datetime import datetime
from uuid import uuid4
from app.db.mongo import db
from app.core.dashboard_auth import create_access_token


def register_user(username: str, password: str, organization: str) -> dict:
    existing = db.dashboard_users.find_one({"username": username})
    if existing:
        return {"error": "Username already exists"}

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    tenant_id = f"tenant-{str(uuid4())[:8]}"
    user_id = str(uuid4())
    user = {
        "_id": user_id,
        "username": username,
        "password_hash": password_hash,
        "tenant_id": tenant_id,
        "organization": organization,
        "role": "admin",
        "created_at": datetime.utcnow(),
    }

    db.dashboard_users.insert_one(user)
    token = create_access_token(user_id, tenant_id, username, organization)

    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "username": username,
            "tenant_id": tenant_id,
            "organization": organization,
            "role": "admin",
        },
    }


def login_user(username: str, password: str) -> dict:
    user = db.dashboard_users.find_one({"username": username})
    if not user:
        return {"error": "Invalid username or password"}

    if not bcrypt.checkpw(
        password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        return {"error": "Invalid username or password"}

    token = create_access_token(
        user["_id"],
        user["tenant_id"],
        user["username"],
        user["organization"],
    )

    return {
        "token": token,
        "user": {
            "user_id": user["_id"],
            "username": user["username"],
            "tenant_id": user["tenant_id"],
            "organization": user["organization"],
            "role": user.get("role", "admin"),
        },
    }


def seed_default_admin():
    """Create a default admin user if no users exist."""
    if db.dashboard_users.count_documents({}) == 0:
        password_hash = bcrypt.hashpw(
            "admin".encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        user_id = str(uuid4())
        db.dashboard_users.insert_one(
            {
                "_id": user_id,
                "username": "admin",
                "password_hash": password_hash,
                "tenant_id": "tenant-demo-001",
                "organization": "Demo Organization",
                "role": "admin",
                "created_at": datetime.utcnow(),
            }
        )

from fastapi import Header, HTTPException
from app.core.config import settings
import jwt
from datetime import datetime, timedelta


def create_access_token(user_id: str, tenant_id: str, username: str, organization: str) -> str:
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "username": username,
        "organization": organization,
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return {
            "user_id": payload["user_id"],
            "tenant_id": payload["tenant_id"],
            "username": payload["username"],
            "organization": payload["organization"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

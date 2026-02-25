from fastapi import APIRouter, HTTPException, Depends
from app.models.dashboard import LoginRequest, RegisterRequest
from app.services.dashboard_auth_service import login_user, register_user
from app.core.dashboard_auth import get_current_user

router = APIRouter(prefix="/dashboard/auth", tags=["Dashboard Auth"])


@router.post("/register")
def register(data: RegisterRequest):
    result = register_user(data.username, data.password, data.organization)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/login")
def login(data: LoginRequest):
    result = login_user(data.username, data.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

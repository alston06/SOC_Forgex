from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    organization: str


class APIKeyCreateRequest(BaseModel):
    name: str


class UpdateIncidentStatusRequest(BaseModel):
    status: str  # OPEN, INVESTIGATING, CONTAINED, RESOLVED


class UpdateIncidentNotesRequest(BaseModel):
    notes: str

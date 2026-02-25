"""API endpoints for agent trigger service."""
from fastapi import APIRouter
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/healthz")
async def health_check() -> dict:
    """Health check endpoint for probes."""
    return {"status": "ok", "service": settings.service_name}

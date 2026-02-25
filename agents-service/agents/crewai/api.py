"""API endpoints for CrewAI service."""
import os
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, BackgroundTasks
import structlog

from ..models import KickoffRequest, KickoffResponse, CrewTaskContext
from ..crewai.config import settings
from ..llm_client import get_cache_stats, clear_cache
from .orchestrator import run_flow_for_detection

logger = structlog.get_logger(__name__)

# In-memory tracking of active flows (for idempotency)
ACTIVE_FLOWS: dict[str, str] = {}  # detection_id -> flow_id

router = APIRouter()


async def internal_auth(authorization: str = Header(...)) -> None:
    """Dependency to validate internal authentication token."""
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid authorization header format")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix
    if token != settings.internal_auth_token:
        logger.warning("Unauthorized access attempt")
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/cache/stats")
async def cache_stats() -> dict:
    """Get LLM cache statistics (both direct client and LangChain/CrewAI caches)."""
    direct_stats = get_cache_stats()

    # SQLite cache file size
    sqlite_path = settings.llm_cache_db_path
    sqlite_size_kb = 0
    if os.path.exists(sqlite_path):
        sqlite_size_kb = round(os.path.getsize(sqlite_path) / 1024, 1)

    return {
        "direct_llm_cache": direct_stats,
        "crewai_langchain_cache": {
            "type": "SQLiteCache",
            "enabled": settings.llm_cache_enabled,
            "db_path": sqlite_path,
            "db_size_kb": sqlite_size_kb,
        },
    }


@router.post("/cache/clear")
async def cache_clear() -> dict:
    """Clear both LLM caches (use with caution!)."""
    clear_cache()

    # Also clear the SQLite cache
    from langchain_core.globals import get_llm_cache
    langchain_cache = get_llm_cache()
    if langchain_cache is not None:
        langchain_cache.clear()

    return {"status": "cleared", "note": "Both direct and CrewAI LangChain caches cleared"}


@router.post("/kickoff", response_model=KickoffResponse, dependencies=[Depends(internal_auth)])
async def kickoff(
    request: KickoffRequest,
    background_tasks: BackgroundTasks,
) -> KickoffResponse:
    """Kickoff a CrewAI analysis flow for a detection.

    Returns immediately with a flow_id, and runs the analysis in the background.
    Idempotent: if a flow for this detection_id already exists, returns the existing flow_id.
    """
    detection = request.detection
    det_id = detection.detection_id

    # Check for idempotency
    if det_id in ACTIVE_FLOWS:
        logger.info(
            "Flow already exists for detection",
            detection_id=det_id,
            flow_id=ACTIVE_FLOWS[det_id],
        )
        return KickoffResponse(
            flow_id=ACTIVE_FLOWS[det_id],
            status="already_started",
        )

    # Generate new flow_id
    flow_id = f"flow-{uuid.uuid4()}"
    ACTIVE_FLOWS[det_id] = flow_id

    logger.info(
        "CrewAI flow started",
        flow_id=flow_id,
        detection_id=det_id,
        tenant_id=detection.tenant_id,
        rule_id=detection.rule_id,
    )

    # Create context
    context = CrewTaskContext(
        flow_id=flow_id,
        detection=detection,
        case_id=None,
        shared_state={},
    )

    # Schedule the CrewAI run in background
    background_tasks.add_task(run_flow_for_detection, context)

    return KickoffResponse(
        flow_id=flow_id,
        status="started",
    )

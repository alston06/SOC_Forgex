"""Internal API endpoints for case service."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from typing import List, Optional
import structlog

from .config import settings
from .models import CaseActionRequest, CaseActionResponse, AgentOutputRequest, AgentOutputResponse, Case
from .storage import storage

logger = structlog.get_logger(__name__)

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


@router.post(
    "/internal/case-action",
    response_model=CaseActionResponse,
    dependencies=[Depends(internal_auth)],
)
async def case_action(request: CaseActionRequest) -> CaseActionResponse:
    """Handle case actions: open, update, close."""
    logger.info(
        "Case action requested",
        action=request.action,
        tenant_id=request.tenant_id,
        detection_id=request.detection_id,
    )

    if request.action == "open":
        # Create new case
        case = storage.create_case(
            tenant_id=request.tenant_id,
            detection_id=request.detection_id,
            severity=request.severity or "MEDIUM",
            summary=request.summary or "New case opened",
        )
        logger.info("Case created", case_id=case.case_id)
        return CaseActionResponse(case_id=case.case_id, status="created")

    elif request.action == "update":
        # Update existing case
        if not request.case_id:
            # Try to find existing case for this detection
            existing = storage.find_by_detection(
                tenant_id=request.tenant_id,
                detection_id=request.detection_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Case not found")
            case_id = existing.case_id
        else:
            case_id = request.case_id

        case = storage.update_case(
            case_id=case_id,
            severity=request.severity,
            summary=request.summary,
        )
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        logger.info("Case updated", case_id=case_id)
        return CaseActionResponse(case_id=case_id, status="updated")

    elif request.action == "close":
        # Close existing case
        if not request.case_id:
            existing = storage.find_by_detection(
                tenant_id=request.tenant_id,
                detection_id=request.detection_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Case not found")
            case_id = existing.case_id
        else:
            case_id = request.case_id

        case = storage.update_case(case_id=case_id, status="closed")
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        logger.info("Case closed", case_id=case_id)
        return CaseActionResponse(case_id=case_id, status="closed")

    else:
        logger.warning("Invalid case action", action=request.action)
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")


@router.post(
    "/internal/agent-output",
    response_model=AgentOutputResponse,
    dependencies=[Depends(internal_auth)],
)
async def agent_output(request: AgentOutputRequest) -> AgentOutputResponse:
    """Store agent output for a case."""
    logger.info(
        "Agent output received",
        case_id=request.case_id,
        agent_type=request.agent_type,
    )

    case = storage.add_agent_output(
        case_id=request.case_id,
        agent_type=request.agent_type,
        output=request.output,
    )

    if not case:
        logger.warning("Case not found for agent output", case_id=request.case_id)
        raise HTTPException(status_code=404, detail="Case not found")

    logger.info("Agent output stored", case_id=request.case_id)
    return AgentOutputResponse(case_id=request.case_id, status="stored")


@router.get(
    "/cases",
    dependencies=[Depends(internal_auth)],
    response_model=List[Case],
)
async def list_cases(
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> List[Case]:
    """List cases, optionally filtered by tenant."""
    logger.info(
        "Listing cases",
        tenant_id=tenant_id,
        limit=limit,
    )
    return storage.list_cases(tenant_id=tenant_id, limit=limit)

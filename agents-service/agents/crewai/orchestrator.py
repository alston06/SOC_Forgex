"""CrewAI flow orchestration logic."""
import structlog

from ..models import CrewTaskContext
from .crew_runner import run_crewai_crew

logger = structlog.get_logger(__name__)


async def run_flow_for_detection(context: CrewTaskContext) -> None:
    """Run the full CrewAI analysis flow for a detection.

    This now uses the full CrewAI framework with agents, tasks, and crew.
    The crew handles the orchestration internally using CrewAI's sequential process.

    Flow (handled by CrewAI):
    1. Orchestrator opens case
    2. Triage Analyst queries logs (30min window)
    3. Orchestrator updates case if severity upgraded
    4. Incident Analyst queries logs (24h window)
    5. Threat Intel analyzes threats
    6. Orchestrator finalizes (no auto-close)
    """
    detection = context.detection

    try:
        logger.info(
            "Starting CrewAI-based incident analysis",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
        )

        # Run the CrewAI crew
        await run_crewai_crew(context)

        logger.info(
            "CrewAI incident analysis completed",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
        )

    except Exception as e:
        logger.error(
            "Error in CrewAI flow",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
            error=str(e),
        )
        # Error handling is done inside run_crewai_crew
        raise

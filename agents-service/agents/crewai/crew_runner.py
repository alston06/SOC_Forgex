"""CrewAI crew definition for incident analysis."""
from crewai import Crew, Process
from ..models import CrewTaskContext, DetectionEvent
from .tasks import create_tasks
import structlog

logger = structlog.get_logger(__name__)


def create_incident_analysis_crew(detection: DetectionEvent) -> Crew:
    """Create a CrewAI crew for incident analysis.

    Args:
        detection: DetectionEvent to analyze

    Returns:
        Configured Crew object
    """
    # Import agents here to avoid circular imports
    from ..agents.orchestrator_agent import orchestrator_agent
    from ..agents.triage_analyst import triage_analyst
    from ..agents.incident_analyst import incident_analyst
    from ..agents.threat_intel import threat_intel

    # Create tasks
    tasks = create_tasks(detection)

    # Create crew with sequential process
    crew = Crew(
        agents=[
            orchestrator_agent,
            triage_analyst,
            incident_analyst,
            threat_intel,
        ],
        tasks=[
            tasks["open_case"],
            tasks["triage_analysis"],
            tasks["update_case"],
            tasks["incident_analysis"],
            tasks["threat_intel"],
            tasks["finalize"],
        ],
        process=Process.sequential,
        verbose=True,
        memory=False,  # Disabled: requires OpenAI embeddings API key
    )

    return crew


async def run_crewai_crew(context: CrewTaskContext) -> None:
    """Run the full CrewAI crew for a detection.

    This replaces the deterministic MVP implementation with true CrewAI orchestration.

    Args:
        context: CrewTaskContext with detection information
    """
    detection = context.detection

    logger.info(
        "Starting CrewAI crew execution",
        flow_id=context.flow_id,
        detection_id=detection.detection_id,
        tenant_id=detection.tenant_id,
    )

    try:
        # Create crew
        crew = create_incident_analysis_crew(detection)

        # Execute crew
        result = crew.kickoff()

        logger.info(
            "CrewAI crew execution completed",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
            result_summary=str(result)[:500],
        )

    except Exception as e:
        logger.error(
            "CrewAI crew execution failed",
            flow_id=context.flow_id,
            detection_id=detection.detection_id,
            error=str(e),
        )
        # Store error as agent output
        if context.case_id:
            from .tool_wrappers import store_agent_output_sync
            try:
                import json
                store_agent_output_sync(
                    case_id=context.case_id,
                    agent_type="commander",
                    output_json=json.dumps({
                        "error": str(e),
                        "status": "failed",
                        "flow_id": context.flow_id,
                    }),
                )
            except Exception:
                pass
        raise

"""CrewAI tasks for incident analysis workflow."""
from crewai import Task
from ..models import DetectionEvent
from ..agents.orchestrator_agent import orchestrator_agent
from ..agents.triage_analyst import triage_analyst
from ..agents.incident_analyst import incident_analyst
from ..agents.threat_intel import threat_intel


def create_tasks(detection: DetectionEvent) -> dict:
    """Create all tasks for the incident analysis workflow.

    Args:
        detection: DetectionEvent to analyze

    Returns:
        Dictionary of task names to Task objects
    """
    detection_dict = detection.model_dump(mode="json")
    description = detection.description or f"Alert {detection.rule_id} triggered"

    # Task 1: Open Case (Orchestrator)
    task_open_case = Task(
        description=(
            f"Open a new case for this security alert:\n"
            f"- Detection ID: {detection.detection_id}\n"
            f"- Rule ID: {detection.rule_id}\n"
            f"- Severity: {detection.severity}\n"
            f"- Confidence: {detection.confidence}\n"
            f"- Description: {description}\n"
            f"- Tenant ID: {detection.tenant_id}\n\n"
            f"Use the open_case_sync tool to create the case. "
            f"Then store your initial output using store_agent_output_sync."
        ),
        expected_output=(
            "A case ID and initial case information stored in the case service."
        ),
        agent=orchestrator_agent,
    )

    # Task 2: Triage Analysis (Triage Analyst)
    task_triage_analysis = Task(
        description=(
            f"Perform rapid triage analysis for this detection:\n"
            f"- Detection ID: {detection.detection_id}\n"
            f"- Severity: {detection.severity}\n"
            f"- Tenant ID: {detection.tenant_id}\n"
            f"- Entities: {detection_dict.get('entities', {})}\n"
            f"- Evidence: {detection_dict.get('evidence', {})}\n\n"
            f"Query logs from the last 30 minutes using query_logs_sync. "
            f"Analyze the event patterns and assess if the severity should be upgraded. "
            f"Store your triage output using store_agent_output_sync."
        ),
        expected_output=(
            "Triage analysis summary including event count, severity recommendation, "
            "key entities, and notes on findings."
        ),
        agent=triage_analyst,
    )

    # Task 3: Case Update (Orchestrator - conditional)
    task_update_case = Task(
        description=(
            f"Review the triage analysis output for case {detection.detection_id}. "
            f"If the triage analyst recommended a severity upgrade, update the case. "
            f"Store the updated case information using store_agent_output_sync."
        ),
        expected_output=(
            "Updated case with new severity if needed, or confirmation that no update is required."
        ),
        agent=orchestrator_agent,
    )

    # Task 4: Incident Analysis (Incident Analyst)
    task_incident_analysis = Task(
        description=(
            f"Perform deep incident analysis for this detection:\n"
            f"- Detection ID: {detection.detection_id}\n"
            f"- Tenant ID: {detection.tenant_id}\n"
            f"- Entities: {detection_dict.get('entities', {})}\n"
            f"- Evidence: {detection_dict.get('evidence', {})}\n\n"
            f"Query logs from the last 24 hours using query_logs_sync. "
            f"Analyze patterns, determine blast radius, identify impacted services and users. "
            f"Store your incident analysis output using store_agent_output_sync."
        ),
        expected_output=(
            "Incident analysis summary including blast radius, affected entities, "
            "pattern analysis, and comprehensive notes."
        ),
        agent=incident_analyst,
    )

    # Task 5: Threat Intelligence (Threat Intel)
    task_threat_intel = Task(
        description=(
            f"Perform threat intelligence enrichment for this detection:\n"
            f"- Detection ID: {detection.detection_id}\n"
            f"- Entities: {detection_dict.get('entities', {})}\n"
            f"- Evidence: {detection_dict.get('evidence', {})}\n\n"
            f"Query logs for threat patterns and analyze against known indicators. "
            f"Identify any known bad IPs, repeated attack patterns, or threat sources. "
            f"Store your threat intelligence output using store_agent_output_sync."
        ),
        expected_output=(
            "Threat intelligence summary including known indicators, threat level, "
            "enrichment data, and recommendations."
        ),
        agent=threat_intel,
    )

    # Task 6: Finalize (Orchestrator)
    task_finalize = Task(
        description=(
            f"Review all analysis outputs for detection {detection.detection_id} "
            f"and provide a final summary. Do NOT auto-close the case - leave it open "
            f"for human review. Store your final output using store_agent_output_sync."
        ),
        expected_output=(
            "Final summary noting that all agents completed analysis "
            f"and"
            f" case remains open for human review."
        ),
        agent=orchestrator_agent,
    )

    return {
        "open_case": task_open_case,
        "triage_analysis": task_triage_analysis,
        "update_case": task_update_case,
        "incident_analysis": task_incident_analysis,
        "threat_intel": task_threat_intel,
        "finalize": task_finalize,
    }

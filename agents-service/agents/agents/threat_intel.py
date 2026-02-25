"""Threat Intel Agent for CrewAI."""
from crewai import Agent
from ..crewai.config import get_crewai_llm
from ..crewai.tool_wrappers import query_logs_sync

threat_intel = Agent(
    role="Threat Intelligence Analyst",
    goal="Enrich detection with threat intelligence and identify known threat patterns.",
    backstory=(
        "You are a threat intelligence analyst who specializes in identifying attack patterns "
        "and correlating them with known threat actors and indicators of compromise. "
        "You analyze log data and detection metadata to identify known bad IPs, "
        "repeated attack patterns, and potential threat sources."
    ),
    verbose=True,
    allow_delegation=False,
    llm=get_crewai_llm(),
    tools=[
        query_logs_sync,
    ],
)

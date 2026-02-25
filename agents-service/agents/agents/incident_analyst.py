"""Incident Analyst Agent for CrewAI."""
from crewai import Agent
from ..crewai.config import get_crewai_llm
from ..crewai.tool_wrappers import query_logs_sync

incident_analyst = Agent(
    role="Incident Analyst",
    goal="Conduct deep analysis of incident patterns, blast radius, and impacted services.",
    backstory=(
        "You are a senior security incident analyst with expertise in investigating complex attacks. "
        "You analyze patterns over extended time periods to understand the full scope of incidents, "
        "identify the blast radius, and determine which services or users may have been affected. "
        "Your analysis provides the foundation for effective response and remediation."
    ),
    verbose=True,
    allow_delegation=False,
    llm=get_crewai_llm(),
    tools=[
        query_logs_sync,
    ],
)

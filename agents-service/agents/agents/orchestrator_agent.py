"""Orchestrator Agent (Incident Commander) for CrewAI."""
from crewai import Agent
from ..crewai.config import get_crewai_llm
from ..crewai.tool_wrappers import (
    open_case_sync,
    update_case_sync,
    close_case_sync,
    store_agent_output_sync,
)

orchestrator_agent = Agent(
    role="Orchestrator (Incident Commander)",
    goal="Coordinate incident response, manage case lifecycle, and ensure all analysis is completed.",
    backstory=(
        "You are an experienced incident commander with deep expertise in security operations. "
        "You oversee the entire incident response process, ensuring all agents complete their tasks "
        "and cases are properly managed. You make high-level decisions about when to open, "
        "update, or close cases."
    ),
    verbose=True,
    allow_delegation=False,
    llm=get_crewai_llm(),
    tools=[
        open_case_sync,
        update_case_sync,
        close_case_sync,
        store_agent_output_sync,
    ],
)

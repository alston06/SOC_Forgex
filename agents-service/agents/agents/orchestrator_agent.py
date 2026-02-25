"""Orchestrator Agent (Incident Commander) for CrewAI."""
from crewai import Agent

from ..crewai.tools.case_tool import (
    case_tool_open,
    case_tool_update,
    case_tool_close,
)
from ..crewai.tools.agent_output import agent_output_tool

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
    tools=[
        # Tools are async, so we handle them differently in the orchestrator
    ],
)

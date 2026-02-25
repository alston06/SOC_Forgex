"""Triage Analyst Agent for CrewAI."""
from crewai import Agent
from ..crewai.config import get_crewai_llm
from ..crewai.tool_wrappers import query_logs_sync

triage_analyst = Agent(
    role="Triage Analyst",
    goal="Quickly assess incident severity and summarize key facts from recent logs.",
    backstory=(
        "You are a security analyst specializing in rapid incident triage. "
        "You can quickly assess the severity of security events and identify the most important "
        "facts from log data. Your goal is to provide a clear initial assessment that guides "
        "the deeper investigation."
    ),
    verbose=True,
    allow_delegation=False,
    llm=get_crewai_llm(),
    tools=[
        query_logs_sync,
    ],
)

from pydantic import BaseModel
from typing import Dict, Any


class AgentOutputRequest(BaseModel):
    case_id: str
    agent_type: str  # triage|analyst|intel|commander
    output: Dict[str, Any]
from pydantic import BaseModel
from typing import Optional


class CaseActionRequest(BaseModel):
    action: str  # open|update|close
    tenant_id: str
    detection_id: str
    severity: Optional[str] = None
    summary: Optional[str] = None
    case_id: Optional[str] = None
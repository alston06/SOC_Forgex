"""In-memory storage for cases (MVP)."""
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from .models import Case, CaseStatus, CaseAction


class CaseStorage:
    """In-memory storage for cases."""

    def __init__(self):
        self._cases: Dict[str, Case] = {}

    def create_case(
        self,
        tenant_id: str,
        detection_id: str,
        severity: str,
        summary: str,
    ) -> Case:
        """Create a new case."""
        case_id = f"case-{uuid.uuid4()}"
        case = Case(
            case_id=case_id,
            tenant_id=tenant_id,
            detection_id=detection_id,
            severity=severity,
            summary=summary,
            status=CaseStatus.OPEN,
        )
        self._cases[case_id] = case
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        """Get a case by ID."""
        return self._cases.get(case_id)

    def find_by_detection(self, tenant_id: str, detection_id: str) -> Optional[Case]:
        """Find a case by tenant and detection ID."""
        for case in self._cases.values():
            if case.tenant_id == tenant_id and case.detection_id == detection_id:
                return case
        return None

    def update_case(
        self,
        case_id: str,
        severity: Optional[str] = None,
        summary: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Case]:
        """Update a case."""
        case = self._cases.get(case_id)
        if not case:
            return None

        if severity:
            case.severity = severity
        if summary:
            case.summary = summary
        if status:
            case.status = status

        case.updated_at = datetime.utcnow()
        return case

    def add_agent_output(self, case_id: str, agent_type: str, output: dict) -> Optional[Case]:
        """Add agent output to a case."""
        case = self._cases.get(case_id)
        if not case:
            return None

        case.agent_outputs.append(
            {
                "agent_type": agent_type,
                "output": output,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        case.updated_at = datetime.utcnow()
        return case

    def list_cases(self, tenant_id: Optional[str] = None, limit: int = 100) -> List[Case]:
        """List cases, optionally filtered by tenant."""
        cases = list(self._cases.values())
        if tenant_id:
            cases = [c for c in cases if c.tenant_id == tenant_id]
        # Sort by created_at descending
        cases.sort(key=lambda c: c.created_at, reverse=True)
        return cases[:limit]

    def delete_case(self, case_id: str) -> bool:
        """Delete a case."""
        if case_id in self._cases:
            del self._cases[case_id]
            return True
        return False

    def count(self) -> int:
        """Get total number of cases."""
        return len(self._cases)


# Global storage instance
storage = CaseStorage()

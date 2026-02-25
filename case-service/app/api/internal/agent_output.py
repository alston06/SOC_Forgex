from fastapi import APIRouter, Depends
from app.core.security import verify_internal_token
from app.models.agent_output import AgentOutputRequest
from app.db.mongo import db
from datetime import datetime

router = APIRouter()


@router.post("/internal/agent-output", dependencies=[Depends(verify_internal_token)])
def agent_output(data: AgentOutputRequest):

    db.incidents.update_one(
        {"_id": data.case_id},
        {
            "$set": {
                f"agent_summary.{data.agent_type}": data.output,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"status": "ok"}
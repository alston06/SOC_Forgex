from fastapi import FastAPI
from app.api.internal.case_actions import router as internal_case_router
from app.api.internal.agent_output import router as agent_router
from app.api.internal.incident_detail import router as internal_incident_router
from app.api.public.incidents import router as public_incidents_router
from app.api.public.webhooks import router as public_webhooks_router

app = FastAPI(title="SOC Case Management Service")

app.include_router(internal_case_router)
app.include_router(agent_router)
app.include_router(internal_incident_router)
app.include_router(public_incidents_router)
app.include_router(public_webhooks_router)
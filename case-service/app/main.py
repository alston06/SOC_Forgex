from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.internal.case_actions import router as internal_case_router
from app.api.internal.agent_output import router as agent_router
from app.api.internal.incident_detail import router as internal_incident_router
from app.api.public.incidents import router as public_incidents_router
from app.api.public.webhooks import router as public_webhooks_router
from app.api.dashboard.auth import router as dashboard_auth_router
from app.api.dashboard.api_keys import router as dashboard_api_keys_router
from app.api.dashboard.incidents import router as dashboard_incidents_router
from app.api.dashboard.alerts import router as dashboard_alerts_router
from app.api.dashboard.stats import router as dashboard_stats_router
from app.api.dashboard.webhooks import router as dashboard_webhooks_router

app = FastAPI(title="SOC Case Management Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Internal routes
app.include_router(internal_case_router)
app.include_router(agent_router)
app.include_router(internal_incident_router)

# Public API routes
app.include_router(public_incidents_router)
app.include_router(public_webhooks_router)

# Dashboard routes
app.include_router(dashboard_auth_router)
app.include_router(dashboard_api_keys_router)
app.include_router(dashboard_incidents_router)
app.include_router(dashboard_alerts_router)
app.include_router(dashboard_stats_router)
app.include_router(dashboard_webhooks_router)


@app.on_event("startup")
def startup():
    from app.services.dashboard_auth_service import seed_default_admin

    seed_default_admin()
"""FastAPI application for CrewAI service."""
import httpx
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import router as kickoff_router
from .config import settings
from ..logging_conf import configure_logging

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Initialize connections and services on startup, cleanup on shutdown.
    """
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("CrewAI service starting", service_name=settings.service_name)

    # Initialize HTTP client for internal service calls
    app.state.http_client = httpx.AsyncClient()
    logger.info("HTTP client initialized")

    yield

    # Cleanup
    logger.info("CrewAI service shutting down")
    await app.state.http_client.aclose()
    logger.info("HTTP client closed")


app = FastAPI(
    title="SOC CrewAI Service",
    description="CrewAI orchestration runtime for automated incident analysis.",
    lifespan=lifespan,
)

# Include kickoff endpoint
app.include_router(kickoff_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}


@app.get("/")
async def root() -> dict:
    """Root endpoint with service info."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "kickoff": "/kickoff (internal)",
            "cache_stats": "/cache/stats",
            "cache_clear": "/cache/clear",
        },
    }

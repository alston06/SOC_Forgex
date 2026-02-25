"""FastAPI application for the case service."""
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import router as internal_router
from .config import settings
from .logging_conf import configure_logging

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Initialize connections and services on startup, cleanup on shutdown.
    """
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("Case service starting", service_name=settings.service_name)

    yield

    # Cleanup
    logger.info("Case service shutting down")


app = FastAPI(
    title="SOC Case Service",
    description="Manages incident cases and stores agent outputs for SOC Forgex.",
    lifespan=lifespan,
)

# Include internal API routes
app.include_router(internal_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}

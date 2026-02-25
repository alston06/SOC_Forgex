"""FastAPI application for the agent trigger service."""
import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import router as health_router
from .config import settings
from .kafka_consumer import consume_detection_events
from ..logging_conf import configure_logging

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Initialize connections and services on startup, cleanup on shutdown.
    """
    import structlog

    logger = structlog.get_logger(__name__)
    logger.info("Agent trigger service starting", service_name=settings.service_name)

    # Start Kafka consumer as background task
    app_state = {}
    app.state.consumer_task = asyncio.create_task(consume_detection_events(app_state))
    logger.info("Kafka consumer task started")

    yield

    # Cleanup
    logger.info("Agent trigger service shutting down")
    app.state.consumer_task.cancel()
    try:
        await app.state.consumer_task
    except asyncio.CancelledError:
        pass

    logger.info("Shutdown complete")


app = FastAPI(
    title="SOC Agent Trigger Service",
    description="Consumes detection events from Kafka and triggers CrewAI analysis flows.",
    lifespan=lifespan,
)

# Include health check routes
app.include_router(health_router)

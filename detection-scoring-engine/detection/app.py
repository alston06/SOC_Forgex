"""FastAPI application for the detection service."""
import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from .config import settings
from .engine import RuleEngine
from .kafka_consumer import consume_normalized_activity
from .kafka_producer import init_producer
from .logging_conf import configure_logging
from .opensearch_client import create_index_template, init_opensearch
from .api.alerts import router as alerts_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle.

    Initialize connections and services on startup, cleanup on shutdown.
    """
    import structlog

    logger = structlog.get_logger(__name__)

    # Initialize OpenSearch
    app.state.opensearch = init_opensearch()
    create_index_template(app.state.opensearch)
    logger.info("OpenSearch initialized")

    # Initialize Kafka producer
    app.state.kafka_producer = await init_producer()

    # Initialize Rule Engine
    rule_engine = RuleEngine(settings.normalized_index_prefix)

    # Start Kafka consumer as background task
    app_state = {
        "opensearch": app.state.opensearch,
        "kafka_producer": app.state.kafka_producer,
    }

    app.state.consumer_task = asyncio.create_task(
        consume_normalized_activity(app_state, rule_engine)
    )
    logger.info("Kafka consumer task started")

    yield

    # Cleanup
    logger.info("Shutting down...")
    app.state.consumer_task.cancel()
    try:
        await app.state.consumer_task
    except asyncio.CancelledError:
        pass

    await app.state.kafka_producer.stop()
    logger.info("Kafka producer stopped")

    app.state.opensearch.close()
    logger.info("OpenSearch client closed")

    logger.info("Shutdown complete")


app = FastAPI(
    title="SOC Detection & Scoring Engine",
    description="Consumes normalized activity events, evaluates detection rules, and publishes detections.",
    lifespan=lifespan,
)

# Include alerts API routes
app.include_router(alerts_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}

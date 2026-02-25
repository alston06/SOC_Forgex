"""FastAPI application for the normalizer service."""
import asyncio

import httpx
from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import router as internal_router
from .config import settings
from .geoip import init_geoip_reader
from .kafka_consumer import consume_raw_activity
from .kafka_producer import init_producer
from .logging_conf import configure_logging
from .opensearch_client import create_index_template, init_opensearch

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

    # Initialize GeoIP reader
    app.state.geoip_reader = init_geoip_reader(settings.geoip_db_path)
    logger.info("GeoIP reader initialized", db_path=settings.geoip_db_path)

    # Initialize HTTP client for user service
    app.state.http_client = httpx.AsyncClient()
    logger.info("HTTP client initialized", base_url=settings.user_service_base_url)

    # Start Kafka consumer as background task
    app_state = {
        "opensearch": app.state.opensearch,
        "kafka_producer": app.state.kafka_producer,
        "geoip_reader": app.state.geoip_reader,
        "http_client": app.state.http_client,
    }

    app.state.consumer_task = asyncio.create_task(consume_raw_activity(app_state))
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

    await app.state.http_client.aclose()
    logger.info("HTTP client closed")

    app.state.geoip_reader.close()
    logger.info("GeoIP reader closed")

    app.state.opensearch.close()
    logger.info("OpenSearch client closed")

    logger.info("Shutdown complete")


app = FastAPI(
    title="SOC Normalizer Service",
    description="Consumes raw activity events, normalizes and enriches them, and publishes to OpenSearch and Kafka.",
    lifespan=lifespan,
)

# Include internal API routes
app.include_router(internal_router, prefix="/internal")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}

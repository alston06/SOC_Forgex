"""FastAPI application for the SOC Ingestion Service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .kafka import start_kafka, stop_kafka
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Kafka producer on startup, stop on shutdown."""
    logger.info("Ingestion service starting …")
    await start_kafka()
    yield
    logger.info("Ingestion service shutting down …")
    await stop_kafka()


app = FastAPI(
    title="SOC Ingestion Service",
    description="Receives security telemetry from the Forgex Security SDK, authenticates, rate-limits, and publishes to Kafka.",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health_check():
    """Simple health-check endpoint."""
    return {"status": "healthy", "service": "soc-ingestion"}

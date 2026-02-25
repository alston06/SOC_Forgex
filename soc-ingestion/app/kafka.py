"""Kafka producer lifecycle — used by the FastAPI lifespan."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer

from .config import settings

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None


async def start_kafka() -> None:
    """Create and start the Kafka producer."""
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode(),
        key_serializer=lambda k: k.encode() if k else None,
    )
    await _producer.start()
    logger.info("Kafka producer started (servers=%s)", settings.kafka_bootstrap_servers)


async def stop_kafka() -> None:
    """Flush and stop the Kafka producer."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer stopped")


async def publish(tenant_id: str, batch: list[Dict[str, Any]]) -> None:
    """Publish a batch envelope to the ``raw-activity`` Kafka topic.

    The normalizer-service expects messages shaped as::

        {"tenant_id": "<str>", "batch": [<event>, ...]}
    """
    if _producer is None:
        logger.warning("Kafka producer not initialised — dropping batch")
        return

    message = {
        "tenant_id": tenant_id,
        "batch": batch,
    }
    await _producer.send_and_wait(
        settings.kafka_topic,
        value=message,
        key=tenant_id,
    )
    logger.debug("Published %d events for tenant %s", len(batch), tenant_id)

"""Kafka producer for normalized activity events."""
import json

import structlog
from aiokafka import AIOKafkaProducer

from .config import settings
from .models import NormalizedActivityEvent

logger = structlog.get_logger(__name__)


async def init_producer() -> AIOKafkaProducer:
    """Initialize and start the Kafka producer.

    Returns:
        Started AIOKafkaProducer instance.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda v: v.encode("utf-8"),
    )
    await producer.start()
    logger.info("Kafka producer started", bootstrap_servers=settings.kafka_bootstrap_servers)
    return producer


async def publish_normalized_event(
    producer: AIOKafkaProducer, normalized_event: NormalizedActivityEvent
) -> None:
    """Publish a normalized event to the normalized-activity topic.

    Args:
        producer: Kafka producer instance.
        normalized_event: The normalized event to publish.
    """
    key = f"{normalized_event.tenant_id}-{normalized_event.event_id}"
    payload = {
        "tenant_id": normalized_event.tenant_id,
        "event": normalized_event.model_dump(mode="json"),
    }

    await producer.send_and_wait(
        settings.kafka_output_topic,
        key=key,
        value=payload,
    )

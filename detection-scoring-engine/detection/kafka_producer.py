"""Kafka producer for detection events."""
import json

import structlog
from aiokafka import AIOKafkaProducer

from .config import settings
from .models import DetectionEvent

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


async def publish_detection(
    producer: AIOKafkaProducer,
    detection: DetectionEvent,
) -> None:
    """Publish a detection event to the detection-events topic.

    Args:
        producer: Kafka producer instance.
        detection: The detection event to publish.
    """
    key = f"{detection.tenant_id}-{detection.detection_id}"
    payload = {
        "tenant_id": detection.tenant_id,
        "detection": detection.model_dump(mode="json", by_alias=True),
    }

    await producer.send_and_wait(
        settings.kafka_output_topic,
        key=key,
        value=payload,
    )

    logger.debug(
        "Detection published",
        detection_id=detection.detection_id,
        tenant_id=detection.tenant_id,
        rule=detection.rule_id,
    )

"""Kafka consumer for raw activity events."""
import json

import structlog
from aiokafka import AIOKafkaConsumer

from .config import settings
from .processor import process_batch_message

logger = structlog.get_logger(__name__)


async def consume_raw_activity(app_state: dict) -> None:
    """Consume raw activity events from the raw-activity topic.

    Args:
        app_state: Shared application state with producer, OpenSearch, etc.
    """
    consumer = AIOKafkaConsumer(
        settings.kafka_input_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    await consumer.start()
    app_state["kafka_consumer"] = consumer
    logger.info(
        "Kafka consumer started",
        topic=settings.kafka_input_topic,
        group_id=settings.kafka_group_id,
    )

    try:
        async for msg in consumer:
            await process_batch_message(msg.value, app_state)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")

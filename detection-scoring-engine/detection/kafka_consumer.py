"""Kafka consumer for normalized activity events."""
import json

import structlog
from aiokafka import AIOKafkaConsumer

from .config import settings
from .processor import process_detection_message

logger = structlog.get_logger(__name__)


async def consume_normalized_activity(app_state: dict, rule_engine) -> None:
    """Consume normalized activity events from the normalized-activity topic.

    Args:
        app_state: Shared application state with producer, OpenSearch, etc.
        rule_engine: RuleEngine instance for event evaluation
    """
    consumer = AIOKafkaConsumer(
        settings.kafka_input_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    await consumer.start()
    app_state["kafka_consumer"] = consumer
    logger.info(
        "Kafka consumer started",
        topic=settings.kafka_input_topic,
        group_id=settings.kafka_consumer_group,
    )

    try:
        async for msg in consumer:
            await process_detection_message(msg.value, app_state, rule_engine)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")

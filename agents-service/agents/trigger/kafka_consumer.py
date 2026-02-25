"""Kafka consumer for agent trigger service."""
import json
from aiokafka import AIOKafkaConsumer
import httpx
import structlog

from .config import settings
from ..models import DetectionEvent

logger = structlog.get_logger(__name__)

INTERNAL_HEADERS = {
    "Authorization": f"Bearer {settings.internal_auth_token}",
    "Content-Type": "application/json",
}


async def handle_detection_event(msg_value: bytes) -> None:
    """Handle a detection event from Kafka."""
    try:
        payload = json.loads(msg_value.decode("utf-8"))
        detection = DetectionEvent(**payload)

        logger.info(
            "Processing detection event",
            detection_id=detection.detection_id,
            tenant_id=detection.tenant_id,
            rule_id=detection.rule_id,
            severity=detection.severity,
        )

        # Send to crewai service
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"{settings.crewai_service_url}{settings.crewai_kickoff_endpoint}"
            resp = await client.post(
                url,
                headers=INTERNAL_HEADERS,
                json={"detection": detection.model_dump(mode="json")},
            )

            if resp.status_code in (200, 202):
                logger.info(
                    "Detection forwarded to crewai service",
                    detection_id=detection.detection_id,
                    status_code=resp.status_code,
                )
            else:
                logger.warning(
                    "Crewai service returned error",
                    detection_id=detection.detection_id,
                    status_code=resp.status_code,
                    response=resp.text,
                )

    except json.JSONDecodeError as e:
        logger.error("Failed to decode detection event", error=str(e))
    except Exception as e:
        logger.error("Error handling detection event", error=str(e))


async def consume_detection_events(app_state: dict) -> None:
    """Consume detection events from Kafka."""
    consumer = AIOKafkaConsumer(
        settings.kafka_input_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        enable_auto_commit=True,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        value_deserializer=lambda v: v,  # Deserialize manually for error handling
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
            await handle_detection_event(msg.value)
    finally:
        await consumer.stop()
        logger.info("Kafka consumer stopped")

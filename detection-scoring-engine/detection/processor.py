"""Detection event processing pipeline."""
from typing import Any, Dict, List

import structlog
from opensearchpy import OpenSearch

from .models import NormalizedActivityEvent, DetectionEvent
from .engine import RuleEngine
from .kafka_producer import publish_detection
from .opensearch_client import index_detection

logger = structlog.get_logger(__name__)


async def process_detection_message(
    message: Dict[str, Any],
    app_state: Dict[str, Any],
    rule_engine: RuleEngine,
) -> None:
    """Process a normalized activity event from Kafka.

    This function:
    1. Validates and deserializes the normalized event
    2. Evaluates against all detection rules
    3. Indexes detections to OpenSearch
    4. Publishes detections to Kafka

    Args:
        message: Deserialized Kafka message with tenant_id and event
        app_state: Shared application state with OpenSearch, producer, etc.
        rule_engine: RuleEngine instance for evaluation
    """
    tenant_id = message.get("tenant_id")
    event_data = message.get("event")

    if not tenant_id or not event_data:
        logger.warning("Invalid detection message", message=message)
        return

    try:
        event = NormalizedActivityEvent(**event_data)
    except Exception as e:
        logger.warning(
            "Failed to parse normalized event",
            error=str(e),
            message=message,
        )
        return

    logger.debug(
        "Processing normalized event",
        tenant_id=tenant_id,
        event_id=event.event_id,
        event_type=event.event_type,
    )

    # Evaluate against all rules
    opensearch: OpenSearch = app_state["opensearch"]
    detections = await rule_engine.evaluate_event(event, opensearch)

    if not detections:
        logger.debug("No detections triggered", event_id=event.event_id)
        return

    logger.info(
        "Detections triggered",
        event_id=event.event_id,
        detection_count=len(detections),
    )

    # Index each detection to OpenSearch
    for detection in detections:
        await index_detection(opensearch, detection)

    # Publish each detection to Kafka
    producer = app_state["kafka_producer"]
    for detection in detections:
        await publish_detection(producer, detection)

    logger.info(
        "Detection processing complete",
        event_id=event.event_id,
        processed_count=len(detections),
    )

"""Batch processing pipeline for normalizing activity events."""
import structlog
from typing import Any, Dict, List

from .enrichment import enrich_user_role, normalize_path
from .geoip import enrich_geoip
from .kafka_producer import publish_normalized_event
from .models import ActivityEvent, NormalizedActivityEvent
from .opensearch_client import index_normalized_events_bulk

logger = structlog.get_logger(__name__)


async def process_batch_message(message: Dict[str, Any], app_state: Dict[str, Any]) -> None:
    """Process a batch of raw activity events from Kafka.

    This function:
    1. Validates the batch envelope (tenant_id, batch)
    2. For each event: validates, enriches, and normalizes
    3. Bulk indexes to OpenSearch
    4. Publishes each normalized event to Kafka

    Args:
        message: Deserialized Kafka message with tenant_id and batch.
        app_state: Shared application state.
    """
    tenant_id = message.get("tenant_id")
    raw_events = message.get("batch") or []

    if not tenant_id or not isinstance(raw_events, list):
        logger.warning("Invalid batch message", message=message)
        return

    logger.debug(
        "Processing batch",
        tenant_id=tenant_id,
        batch_size=len(raw_events),
    )

    normalized_events: List[NormalizedActivityEvent] = []

    for raw in raw_events:
        try:
            activity = ActivityEvent(**raw)
        except Exception as e:
            logger.warning("Failed to parse activity event", error=str(e))
            continue

        # Generate event ID
        event_id = str(activity.timestamp.timestamp()).replace(".", "-") + "-" + activity.event_type

        # Enrich and normalize
        norm_path = normalize_path(activity.resource)
        geo_country, geo_city = enrich_geoip(
            app_state["geoip_reader"], activity.ip
        )
        user_role = await enrich_user_role(
            app_state["http_client"], activity.actor
        )

        normalized = NormalizedActivityEvent(
            **activity.model_dump(),
            tenant_id=tenant_id,
            geo_country=geo_country,
            geo_city=geo_city,
            user_role=user_role,
            normalized_path=norm_path,
            risk_score=0.0,
            event_id=event_id,
        )
        normalized_events.append(normalized)

    if not normalized_events:
        logger.debug("No events normalized", tenant_id=tenant_id)
        return

    # Index into OpenSearch
    await index_normalized_events_bulk(
        app_state["opensearch"], normalized_events
    )

    # Publish each normalized event to Kafka
    producer = app_state["kafka_producer"]
    for ne in normalized_events:
        await publish_normalized_event(producer, ne)

    logger.info(
        "Processed batch",
        tenant_id=tenant_id,
        normalized_count=len(normalized_events),
    )

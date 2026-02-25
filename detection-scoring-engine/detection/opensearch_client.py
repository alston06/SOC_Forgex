"""OpenSearch client for detections."""
from collections import defaultdict
from datetime import datetime
from typing import List

import structlog
from opensearchpy import OpenSearch

from .config import settings
from .models import DetectionEvent

logger = structlog.get_logger(__name__)


def init_opensearch() -> OpenSearch:
    """Initialize OpenSearch client with basic auth.

    Returns:
        Configured OpenSearch client.
    """
    client = OpenSearch(
        hosts=[str(settings.opensearch_url)],
        http_auth=(settings.opensearch_username, settings.opensearch_password),
        use_ssl=False,
        verify_certs=False,
        timeout=5,
        max_retries=3,
        retry_on_timeout=True,
    )
    return client


def create_index_template(client: OpenSearch) -> None:
    """Create the detections index template if it doesn't exist.

    Args:
        client: OpenSearch client.
    """
    template_name = "detections-template"
    if client.indices.exists_template(name=template_name):
        logger.info("Index template already exists", template=template_name)
        return

    template_body = {
        "index_patterns": ["detections-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
            },
            "mappings": {
                "properties": {
                    "detection_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "detection_timestamp": {"type": "date"},
                    "rule_name": {"type": "keyword"},
                    "rule_id": {"type": "keyword"},
                    "rule_description": {"type": "text"},
                    "severity": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "risk_score": {"type": "float"},
                    "created_at": {"type": "date"},
                    "correlation_id": {"type": "keyword"},
                    "context": {"enabled": False},  # Dynamic fields
                    # Nested triggering_event
                    "triggering_event": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "event_id": {"type": "keyword"},
                            "event_type": {"type": "keyword"},
                            "actor": {"type": "keyword"},
                            "resource": {"type": "keyword"},
                            "action": {"type": "keyword"},
                            "ip": {"type": "ip"},
                            "normalized_path": {"type": "keyword"},
                            "service_name": {"type": "keyword"},
                            "tenant_id": {"type": "keyword"},
                            "geo_country": {"type": "keyword"},
                            "geo_city": {"type": "keyword"},
                            "user_role": {"type": "keyword"},
                            "risk_score": {"type": "float"},
                            "extras": {"enabled": False},
                        }
                    },
                }
            },
        },
    }

    client.indices.put_template(name=template_name, body=template_body)
    logger.info("Created index template", template=template_name)


async def index_detection(client: OpenSearch, detection: DetectionEvent) -> None:
    """Index a single detection event to OpenSearch.

    Args:
        client: OpenSearch client.
        detection: Detection event to index.
    """
    ts: datetime = detection.detection_timestamp
    month = ts.strftime("%Y-%m")
    index_name = f"{settings.detection_index_prefix}{detection.tenant_id}-{month}"

    try:
        client.index(
            index=index_name,
            id=detection.detection_id,
            body=detection.model_dump(),
            refresh=False,
        )
        logger.debug(
            "Detection indexed",
            detection_id=detection.detection_id,
            index=index_name,
        )
    except Exception as e:
        logger.error(
            "Failed to index detection",
            detection_id=detection.detection_id,
            error=str(e),
        )


async def index_detections_bulk(
    client: OpenSearch,
    detections: List[DetectionEvent],
) -> None:
    """Bulk index detections to OpenSearch.

    Groups detections by tenant_id and month for efficient indexing.

    Args:
        client: OpenSearch client.
        detections: List of detections to index.
    """
    if not detections:
        return

    # Group detections by index name
    buckets = defaultdict(list)
    for d in detections:
        ts: datetime = d.detection_timestamp
        month = ts.strftime("%Y-%m")
        index_name = f"{settings.detection_index_prefix}{d.tenant_id}-{month}"
        buckets[index_name].append(d)

    # Build and execute bulk requests per index
    for index_name, detections_list in buckets.items():
        body = []
        for d in detections_list:
            body.append({"index": {"_index": index_name, "_id": d.detection_id}})
            body.append(d.model_dump())

        if not body:
            continue

        try:
            resp = client.bulk(body=body, refresh=False)
            errors = resp.get("errors")
            if errors:
                logger.warning(
                    "Bulk indexing completed with errors",
                    index=index_name,
                    count=len(detections_list),
                )
            else:
                logger.info(
                    "Bulk indexed detections",
                    index=index_name,
                    count=len(detections_list),
                )
        except Exception as e:
            logger.error(
                "Bulk indexing failed",
                index=index_name,
                error=str(e),
            )

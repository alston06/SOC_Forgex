"""OpenSearch client and indexing functions."""
import structlog
from collections import defaultdict
from datetime import datetime
from typing import List

from opensearchpy import OpenSearch

from .config import settings
from .models import NormalizedActivityEvent

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
    """Create the logs index template if it doesn't exist.

    Args:
        client: OpenSearch client.
    """
    template_name = "logs-template"
    if client.indices.exists_template(name=template_name):
        logger.info("Index template already exists", template=template_name)
        return

    template_body = {
        "index_patterns": ["logs-*"],
        "template": {
            "settings": {"number_of_shards": 1, "number_of_replicas": 1},
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "event_id": {"type": "keyword"},
                    "tenant_id": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "actor": {"type": "keyword"},
                    "resource": {"type": "keyword"},
                    "action": {"type": "keyword"},
                    "ip": {"type": "ip"},
                    "normalized_path": {"type": "keyword"},
                    "service_name": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                    "geo_country": {"type": "keyword"},
                    "geo_city": {"type": "keyword"},
                    "risk_score": {"type": "float"},
                    "extras": {"enabled": False},
                }
            },
        },
    }

    client.indices.put_template(name=template_name, body=template_body)
    logger.info("Created index template", template=template_name)


def index_normalized_events_bulk(
    client: OpenSearch, events: List[NormalizedActivityEvent]
) -> None:
    """Bulk index normalized events to OpenSearch.

    Groups events by tenant_id and month for efficient indexing.

    Args:
        client: OpenSearch client.
        events: List of normalized events to index.
    """
    if not events:
        return

    # Group events by index name (tenant_id + month)
    buckets = defaultdict(list)
    for e in events:
        ts: datetime = e.timestamp
        month = ts.strftime("%Y-%m")
        index_name = f"logs-{e.tenant_id}-{month}"
        buckets[index_name].append(e)

    # Build and execute bulk requests per index
    for index_name, evs in buckets.items():
        body = []
        for e in evs:
            body.append({"index": {"_index": index_name, "_id": e.event_id}})
            body.append(e.model_dump(mode="json"))

        if not body:
            continue

        try:
            resp = client.bulk(body=body, refresh=False)
            errors = resp.get("errors")
            if errors:
                logger.warning(
                    "Bulk indexing completed with errors",
                    index=index_name,
                    count=len(evs),
                )
            else:
                logger.info(
                    "Bulk indexed events",
                    index=index_name,
                    count=len(evs),
                )
        except Exception as e:
            logger.error(
                "Bulk indexing failed",
                index=index_name,
                error=str(e),
            )

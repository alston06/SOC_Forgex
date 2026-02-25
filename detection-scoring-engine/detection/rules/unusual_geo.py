"""Unusual Geography Detection Rule."""
from datetime import timedelta
from typing import Optional

import structlog
from opensearchpy import OpenSearch

from .base import BaseRule
from ..models import NormalizedActivityEvent, DetectionEvent, DetectionSeverity

logger = structlog.get_logger(__name__)


class UnusualGeoRule(BaseRule):
    """Detect logins from countries not seen in the last 30 days."""

    def __init__(self):
        super().__init__(
            rule_id="unusual-geo-001",
            rule_name="Unusual Geographic Login",
            rule_description="Successful login from a country not seen in the last 30 days",
            severity=DetectionSeverity.MEDIUM,
        )

    async def evaluate(
        self,
        event: NormalizedActivityEvent,
        opensearch: OpenSearch,
        normalized_index_prefix: str,
    ) -> Optional[DetectionEvent]:
        # Only evaluate successful logins with geo data
        if event.event_type != "auth" or event.action != "login_success":
            return None

        if not event.actor or not event.geo_country:
            logger.debug("Missing actor or geo for unusual geo check", event_id=event.event_id)
            return None

        # Query for countries seen in last 30 days
        time_window = timedelta(days=30)
        time_from = event.timestamp - time_window
        time_to = event.timestamp

        index_pattern = f"{normalized_index_prefix}{event.tenant_id}-*"

        query = {
            "bool": {
                "must": [
                    {"term": {"tenant_id": event.tenant_id}},
                    {"term": {"event_type": "auth"}},
                    {"term": {"action": "login_success"}},
                    {"term": {"actor": event.actor}},
                    {"exists": {"field": "geo_country"}},
                    {
                        "range": {
                            "timestamp": {
                                "gte": time_from.isoformat(),
                                "lte": time_to.isoformat(),
                            }
                        }
                    },
                ]
            }
        }

        # Use aggregation to get unique countries
        try:
            response = opensearch.search(
                index=index_pattern,
                body={
                    "query": query,
                    "size": 0,  # We only need aggregations
                    "aggs": {
                        "countries": {
                            "terms": {
                                "field": "geo_country",
                                "size": 100,  # Max 100 unique countries
                            }
                        }
                    },
                },
            )

            countries_agg = response.get("aggregations", {}).get("countries", {})
            buckets = countries_agg.get("buckets", [])
            seen_countries = {bucket["key"] for bucket in buckets}

            current_country = event.geo_country

            if current_country not in seen_countries:
                logger.info(
                    "Unusual geo detected",
                    actor=event.actor,
                    country=current_country,
                    seen_countries=len(seen_countries),
                    event_id=event.event_id,
                )

                context = {
                    "new_country": current_country,
                    "seen_countries_count": len(seen_countries),
                    "time_window_days": 30,
                    "actor": event.actor,
                    "geo_city": event.geo_city,
                    "ip": event.ip,
                }

                risk_score = 0.6  # Medium risk for new country

                return self.create_detection(event, context=context, risk_score=risk_score)

        except Exception as e:
            logger.error(
                "Failed to query for unusual geo",
                rule=self.rule_id,
                error=str(e),
                event_id=event.event_id,
            )

        return None

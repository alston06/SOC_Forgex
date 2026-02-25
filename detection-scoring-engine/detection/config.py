"""Configuration for the detection service."""
from pathlib import Path
from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "detection"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_consumer_group: str = "detections-v1"
    kafka_input_topic: str = "normalized-activity"
    kafka_output_topic: str = "detection-events"

    # OpenSearch
    opensearch_url: AnyUrl = AnyUrl("http://opensearch:9200")
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"

    # Index prefixes
    detection_index_prefix: str = "detections-"
    normalized_index_prefix: str = "logs-"

    # API
    port: int = 8005
    internal_auth_token: str = "soc-internal-token-v1"

    # Logging
    log_level: str = "INFO"

    # Detection timeouts (for OS queries)
    os_query_timeout: int = 5  # seconds

    class Config:
        """Pydantic config."""
        env_prefix = "DETECTION_"
        env_file = Path(__file__).parent.parent / ".env"


settings = Settings()

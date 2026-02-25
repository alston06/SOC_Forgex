"""Configuration for the normalizer service."""
from pathlib import Path
from pydantic import AnyUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "normalizer"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "normalizer-v1"
    kafka_input_topic: str = "raw-activity"
    kafka_output_topic: str = "normalized-activity"
    opensearch_url: AnyUrl = AnyUrl("http://localhost:9200")
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    geoip_db_path: str = "./data/GeoLite2-City.mmdb"
    user_service_base_url: str = "http://localhost:8080"
    user_service_timeout_s: float = 0.1
    max_enrich_concurrency: int = 50
    internal_auth_token: str = "soc-internal-token-v1"
    log_level: str = "INFO"

    class Config:
        """Pydantic config."""
        env_prefix = "NORMALIZER_"
        env_path = Path(__file__).parent.parent / ".env"


settings = Settings()

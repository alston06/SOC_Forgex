"""Configuration for the agent trigger service."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "agent-trigger-service"
    port: int = 8002
    log_level: str = "INFO"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_input_topic: str = "detection-events"
    kafka_group_id: str = "agent-trigger-v1"
    kafka_auto_offset_reset: str = "earliest"

    # CrewAI Service (HTTP target)
    crewai_service_url: str = "http://crewai-service:8003"
    crewai_kickoff_endpoint: str = "/kickoff"

    # Internal Auth
    internal_auth_token: str = "soc-internal-token-v1"

    class Config:
        """Pydantic config."""
        env_prefix = "TRIGGER_"
        env_file = Path(__file__).parent.parent.parent / ".env"


settings = Settings()

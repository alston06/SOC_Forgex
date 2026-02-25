"""Configuration for the case service."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "case-service"
    port: int = 8004
    internal_auth_token: str = "soc-internal-token-v1"
    log_level: str = "INFO"
    max_cases: int = 10000

    class Config:
        """Pydantic config."""
        env_prefix = "CASE_"
        env_file = Path(__file__).parent.parent / ".env"


settings = Settings()

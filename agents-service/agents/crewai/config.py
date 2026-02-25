"""Configuration for the CrewAI service."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "crewai-service"
    port: int = 8003
    log_level: str = "INFO"

    # Internal Services
    normalizer_service_url: str = "http://normalizer-service:8001"
    normalizer_log_query_endpoint: str = "/internal/query-logs"
    case_service_url: str = "http://case-service:8004"
    case_action_endpoint: str = "/internal/case-action"
    agent_output_endpoint: str = "/internal/agent-output"

    # Internal Auth
    internal_auth_token: str = "soc-internal-token-v1"

    # Flow Configuration
    max_flow_duration_seconds: int = 3600
    agent_timeout_seconds: int = 300

    # LLM Provider Configuration (OpenRouter or OpenAI)
    llm_provider: str = "openrouter"  # "openrouter" | "openai"
    llm_api_key: str = ""  # OpenRouter API key or OpenAI API key
    llm_api_base: str = "https://openrouter.ai/api/v1"  # OpenRouter base URL
    llm_model: str = "openai/gpt-4"  # OpenRouter model ID
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # Caching Configuration
    llm_cache_enabled: bool = True
    llm_cache_ttl_seconds: int = 3600  # 1 hour

    class Config:
        """Pydantic config."""
        env_prefix = "CREWAI_"
        env_file = Path(__file__).parent.parent / ".env"


settings = Settings()

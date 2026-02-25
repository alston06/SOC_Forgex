"""Configuration for the CrewAI service."""
from pathlib import Path
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
import structlog

_logger = structlog.get_logger(__name__)


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
    llm_cache_db_path: str = "/tmp/crewai_llm_cache.db"  # SQLite cache path

    class Config:
        """Pydantic config."""
        env_prefix = "CREWAI_"
        env_file = Path(__file__).parent.parent / ".env"


settings = Settings()

# ── Persistent SQLite LLM cache for CrewAI agents ──────────────────
# This caches ALL LangChain ChatOpenAI calls (used by every CrewAI agent)
# to a local SQLite DB so identical prompts are never re-sent to the API.
# The cache survives container restarts if mounted to a volume.
if settings.llm_cache_enabled:
    _cache = SQLiteCache(database_path=settings.llm_cache_db_path)
    set_llm_cache(_cache)
    _logger.info(
        "LangChain SQLite LLM cache enabled for CrewAI agents",
        db_path=settings.llm_cache_db_path,
    )
else:
    _logger.info("LangChain LLM cache disabled")


def get_crewai_llm():
    """Get LangChain LLM instance for CrewAI."""
    if settings.llm_provider == "openrouter":
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    else:  # openai
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

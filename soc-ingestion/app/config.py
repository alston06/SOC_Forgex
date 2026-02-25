"""Configuration for the ingestion service."""

from pydantic_settings import BaseSettings
from pymongo import MongoClient
import redis


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    service_name: str = "soc-ingestion"
    port: int = 8000

    # MongoDB
    mongo_uri: str = "mongodb://mongo:27017"
    db_name: str = "soc_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "raw-activity"

    # Rate limiting
    rate_limit_per_minute: int = 300

    class Config:
        env_prefix = "INGESTION_"
        env_file = ".env"


settings = Settings()

# ---------------------------------------------------------------------------
# Shared singletons (created at import time — fast-enough for a small service)
# ---------------------------------------------------------------------------

_mongo_client: MongoClient = MongoClient(settings.mongo_uri)
db = _mongo_client[settings.db_name]

redis_client: redis.Redis = redis.Redis.from_url(
    settings.redis_url, decode_responses=True
)

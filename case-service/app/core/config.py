from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "soc_db"
    INTERNAL_TOKEN: str = "soc-internal-token-v1"
    JWT_SECRET: str = "soc-dashboard-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    DETECTION_SERVICE_URL: str = "http://detection-service:8005"
    NORMALIZER_SERVICE_URL: str = "http://normalizer-service:8001"

    class Config:
        env_file = ".env"


settings = Settings()
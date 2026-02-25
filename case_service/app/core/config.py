from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "soc_db"
    INTERNAL_TOKEN: str = "soc-internal-token-v1"

    class Config:
        env_file = ".env"


settings = Settings()
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+psycopg://tradepilot:tradepilot@localhost:5432/tradepilot"
    redis_url: str = "redis://localhost:6379/0"
    live_trading_enabled: bool = False
    broker_credential_encryption_key: str = "replace-with-fernet-key"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


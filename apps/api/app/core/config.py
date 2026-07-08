from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://tradepilot:tradepilot@localhost:5432/tradepilot",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default="replace-with-a-32-char-jwt-secret-key", alias="JWT_SECRET")
    live_trading_enabled: bool = Field(default=False, alias="LIVE_TRADING_ENABLED")
    enable_live_broker_orders: bool = Field(default=False, alias="ENABLE_LIVE_BROKER_ORDERS")
    enable_auto_trading: bool = Field(default=False, alias="ENABLE_AUTO_TRADING")
    auto_trading_enabled: bool = Field(default=False, alias="AUTO_TRADING_ENABLED")
    paper_trading: bool = Field(default=True, alias="PAPER_TRADING")
    rate_limit_per_minute: int = Field(default=600, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    duplicate_order_window_seconds: int = Field(default=30, alias="DUPLICATE_ORDER_WINDOW_SECONDS")
    broker_timeout_seconds: float = Field(default=10.0, alias="BROKER_TIMEOUT_SECONDS")
    broker_circuit_breaker_threshold: int = Field(default=3, alias="BROKER_CIRCUIT_BREAKER_THRESHOLD")
    broker_circuit_breaker_cooldown_seconds: int = Field(default=30, alias="BROKER_CIRCUIT_BREAKER_COOLDOWN_SECONDS")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3010",
            "http://localhost:3012",
            "http://localhost:3013",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3010",
            "http://127.0.0.1:3012",
            "http://127.0.0.1:3013",
        ],
        alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_driver(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if isinstance(value, str) and value.startswith("postgresql://") and "+psycopg" not in value:
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

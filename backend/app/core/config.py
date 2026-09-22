from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Stock AI"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+psycopg://stockuser:stockpass@db:5432/stock_ai"
    redis_url: str | None = "redis://redis:6379/0"

    # Upstream data is cached to keep repeated views -- and, later, several agents
    # analysing one ticker -- from each costing a provider request.
    cache_ttl_daily_seconds: int = 900
    cache_ttl_intraday_seconds: int = 300
    cache_ttl_quote_seconds: int = 60

    # Yahoo's feed answers 404 to httpx's default User-Agent and 200 to anything else.
    http_user_agent: str = "StockSage/0.1"

    # The SEC rejects requests whose User-Agent names no contact address -- 403, not a
    # warning. Set SEC_USER_AGENT to something like "StockSage/0.1 (you@example.com)"
    # to enable filings; until then that source is skipped. No address ships in the repo.
    sec_user_agent: str = "StockSage/0.1"
    news_lookback_days: int = 14

    openai_api_key: str | None = None
    openai_model: str | None = None

    twelve_data_api_key: str | None = None
    finnhub_api_key: str | None = None
    alpha_vantage_api_key: str | None = None
    fred_api_key: str | None = None

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = None
    s3_bucket: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""A caching decorator around any MarketDataProvider."""

import json
import logging
from datetime import datetime

from redis.asyncio import Redis

from app.core.cache import cache_get, cache_set
from app.core.config import Settings
from app.providers.base import MarketDataProvider, PriceBar, Quote


logger = logging.getLogger(__name__)

CACHE_VERSION = "v1"


class CachedMarketDataProvider(MarketDataProvider):
    """Serves repeated requests from Redis instead of re-hitting the provider.

    Only non-empty results are cached. An empty history is how this provider reports
    both an unknown ticker and a transient upstream failure, and caching the latter
    would keep a passing outage alive for the whole TTL.
    """

    def __init__(self, provider: MarketDataProvider, client: Redis | None, settings: Settings) -> None:
        self.provider = provider
        self.client = client
        self.settings = settings

    @property
    def name(self) -> str:
        return self.provider.name

    async def get_price_history(self, ticker: str, interval: str, period: str) -> list[PriceBar]:
        key = f"stocksage:{CACHE_VERSION}:history:{self.provider.name}:{ticker}:{interval}:{period}"
        cached = await cache_get(self.client, key)
        if cached is not None:
            try:
                return [_bar_from_dict(row) for row in json.loads(cached)]
            except Exception:
                logger.warning("discarding unreadable cache entry", exc_info=True, extra={"cache_key": key})

        bars = await self.provider.get_price_history(ticker, interval, period)
        if bars:
            ttl = (
                self.settings.cache_ttl_intraday_seconds
                if interval != "1d"
                else self.settings.cache_ttl_daily_seconds
            )
            await cache_set(self.client, key, json.dumps([_bar_to_dict(bar) for bar in bars]), ttl)
        return bars

    async def get_quote(self, ticker: str) -> Quote:
        key = f"stocksage:{CACHE_VERSION}:quote:{self.provider.name}:{ticker}"
        cached = await cache_get(self.client, key)
        if cached is not None:
            try:
                return Quote(**json.loads(cached))
            except Exception:
                logger.warning("discarding unreadable cache entry", exc_info=True, extra={"cache_key": key})

        quote = await self.provider.get_quote(ticker)
        if quote.current_price is not None:
            await cache_set(
                self.client, key, json.dumps(quote.__dict__), self.settings.cache_ttl_quote_seconds
            )
        return quote


def _bar_to_dict(bar: PriceBar) -> dict[str, object]:
    row = dict(bar.__dict__)
    row["timestamp"] = bar.timestamp.isoformat()
    return row


def _bar_from_dict(row: dict[str, object]) -> PriceBar:
    return PriceBar(**{**row, "timestamp": datetime.fromisoformat(str(row["timestamp"]))})

from typing import Any

import pytest

from app.core.config import Settings
from app.providers.cached import CachedMarketDataProvider
from tests.fakes import FakeMarketDataProvider


class StubRedis:
    """An in-memory stand-in; `failing` makes every call raise, as an outage would."""

    def __init__(self, failing: bool = False) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.failing = failing

    async def get(self, key: str) -> str | None:
        if self.failing:
            raise ConnectionError("redis is down")
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if self.failing:
            raise ConnectionError("redis is down")
        self.store[key] = value
        self.ttls[key] = ttl


@pytest.fixture
def settings() -> Settings:
    return Settings(cache_ttl_daily_seconds=900, cache_ttl_intraday_seconds=300, cache_ttl_quote_seconds=60)


def wrap(inner: FakeMarketDataProvider, client: Any, settings: Settings) -> CachedMarketDataProvider:
    return CachedMarketDataProvider(inner, client, settings)


async def test_repeated_request_hits_the_provider_once(settings: Settings) -> None:
    inner = FakeMarketDataProvider(bar_count=30)
    cached = wrap(inner, StubRedis(), settings)

    first = await cached.get_price_history("NVDA", "1d", "6m")
    second = await cached.get_price_history("NVDA", "1d", "6m")

    assert len(inner.history_calls) == 1
    assert first == second


async def test_each_window_is_cached_separately(settings: Settings) -> None:
    inner = FakeMarketDataProvider(bar_count=30)
    cached = wrap(inner, StubRedis(), settings)

    for interval, period in (("1d", "6m"), ("1d", "1y"), ("1h", "6m")):
        await cached.get_price_history("NVDA", interval, period)
    await cached.get_price_history("AAPL", "1d", "6m")

    assert len(inner.history_calls) == 4


async def test_bars_survive_the_round_trip_unchanged(settings: Settings) -> None:
    inner = FakeMarketDataProvider(bar_count=5)
    client = StubRedis()

    direct = await inner.get_price_history("NVDA", "1d", "6m")
    await wrap(FakeMarketDataProvider(bar_count=5), client, settings).get_price_history("NVDA", "1d", "6m")
    from_cache = await wrap(FakeMarketDataProvider(bar_count=99), client, settings).get_price_history(
        "NVDA", "1d", "6m"
    )

    assert from_cache == direct
    assert from_cache[0].timestamp.tzinfo is not None


async def test_intraday_expires_sooner_than_daily(settings: Settings) -> None:
    client = StubRedis()
    cached = wrap(FakeMarketDataProvider(bar_count=5), client, settings)

    await cached.get_price_history("NVDA", "1d", "6m")
    await cached.get_price_history("NVDA", "1h", "6m")

    ttls = sorted(client.ttls.values())
    assert ttls == [300, 900]


async def test_empty_history_is_not_cached(settings: Settings) -> None:
    """An empty result also means a transient upstream failure; caching it prolongs one."""
    inner = FakeMarketDataProvider(bar_count=0)
    client = StubRedis()
    cached = wrap(inner, client, settings)

    await cached.get_price_history("NVDA", "1d", "6m")
    await cached.get_price_history("NVDA", "1d", "6m")

    assert client.store == {}
    assert len(inner.history_calls) == 2


async def test_a_redis_outage_does_not_break_requests(settings: Settings) -> None:
    inner = FakeMarketDataProvider(bar_count=30)
    cached = wrap(inner, StubRedis(failing=True), settings)

    bars = await cached.get_price_history("NVDA", "1d", "6m")

    assert len(bars) == 30
    assert len(inner.history_calls) == 1


async def test_no_redis_configured_falls_straight_through(settings: Settings) -> None:
    inner = FakeMarketDataProvider(bar_count=30)
    cached = wrap(inner, None, settings)

    assert len(await cached.get_price_history("NVDA", "1d", "6m")) == 30
    assert len(await cached.get_price_history("NVDA", "1d", "6m")) == 30
    assert len(inner.history_calls) == 2


async def test_quotes_are_cached_and_keep_the_provider_name(settings: Settings) -> None:
    inner = FakeMarketDataProvider()
    cached = wrap(inner, StubRedis(), settings)

    first = await cached.get_quote("NVDA")
    second = await cached.get_quote("NVDA")

    assert cached.name == "fake"
    assert first == second
    assert inner.quote_calls == ["NVDA"]


async def test_a_quote_without_a_price_is_not_cached(settings: Settings) -> None:
    """No price means the lookup did not resolve; that is not worth remembering."""
    inner = FakeMarketDataProvider()
    inner.quote_price = None
    cached = wrap(inner, StubRedis(), settings)

    await cached.get_quote("NVDA")
    await cached.get_quote("NVDA")

    assert inner.quote_calls == ["NVDA", "NVDA"]

from datetime import UTC, datetime, timedelta
import asyncio

import pytest

from app.pipelines.prices import InvalidTickerError, PricePipeline, normalize_price_bars, normalize_ticker
from app.providers.base import MarketDataProvider, PriceBar, Quote


class FakeMarketDataProvider(MarketDataProvider):
    name = "fake"

    async def get_price_history(self, ticker: str, interval: str, period: str) -> list[PriceBar]:
        return [
            PriceBar(
                ticker=ticker,
                timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
                open=100 + index,
                high=102 + index,
                low=99 + index,
                close=101 + index,
                adjusted_close=101 + index,
                volume=1_000_000 + index,
                interval=interval,
                provider=self.name,
            )
            for index in range(30)
        ]

    async def get_quote(self, ticker: str) -> Quote:
        return Quote(ticker=ticker, current_price=123.45, name="Fake Corp", exchange="NMS", currency="USD", provider=self.name)


def test_normalize_ticker_accepts_common_symbols() -> None:
    assert normalize_ticker(" nvda ") == "NVDA"
    assert normalize_ticker("brk.b") == "BRK.B"


def test_normalize_ticker_rejects_invalid_symbols() -> None:
    with pytest.raises(InvalidTickerError):
        normalize_ticker("NVDA;DROP")


def test_normalize_price_bars_removes_invalid_and_duplicates() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    bars = [
        PriceBar("MSFT", timestamp, 10, 12, 9, 11, 11, 100, "1d", "fake"),
        PriceBar("MSFT", timestamp, 10, 12, 9, 11, 11, 100, "1d", "fake"),
        PriceBar("MSFT", timestamp + timedelta(days=1), 10, 8, 9, 11, 11, 100, "1d", "fake"),
    ]

    cleaned = normalize_price_bars(bars)

    assert len(cleaned) == 1
    assert cleaned[0].ticker == "MSFT"


def test_price_pipeline_returns_response_without_database() -> None:
    pipeline = PricePipeline(FakeMarketDataProvider())

    response = asyncio.run(pipeline.get_prices("nvda", "1d", "1m"))

    assert response.ticker == "NVDA"
    assert response.provider == "fake"
    assert len(response.prices) == 30
    assert response.snapshot is not None
    assert response.data_quality.providers_available == ["fake"]

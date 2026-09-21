from datetime import UTC, datetime, timedelta

import pytest

from app.pipelines.prices import (
    InsufficientDataError,
    InvalidTickerError,
    PricePipeline,
    ProviderError,
    normalize_price_bars,
    normalize_ticker,
)
from app.providers.base import PriceBar
from tests.fakes import FakeMarketDataProvider


def test_normalize_ticker_accepts_common_symbols() -> None:
    assert normalize_ticker(" nvda ") == "NVDA"
    assert normalize_ticker("brk.b") == "BRK-B"


def test_class_shares_normalize_to_the_resolvable_spelling() -> None:
    """BRK.B returns nothing upstream; BRK-B is the same security and does resolve."""
    assert normalize_ticker("BRK.B") == "BRK-B"
    assert normalize_ticker("bf.b") == "BF-B"
    assert normalize_ticker("BRK-B") == "BRK-B"


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


async def test_price_pipeline_returns_response_without_database() -> None:
    pipeline = PricePipeline(FakeMarketDataProvider())

    response = await pipeline.get_prices("nvda", "1d", "1m")

    assert response.ticker == "NVDA"
    assert response.provider == "fake"
    assert len(response.prices) == 30
    assert response.snapshot is not None
    assert response.data_quality.providers_available == ["fake"]


async def test_price_pipeline_raises_on_provider_failure() -> None:
    """A failing provider must not be reported as a successful, empty response."""
    pipeline = PricePipeline(FakeMarketDataProvider(failure=RuntimeError("yahoo down")))

    with pytest.raises(ProviderError):
        await pipeline.get_prices("NVDA", "1d", "6m")


async def test_price_pipeline_raises_when_provider_returns_nothing() -> None:
    pipeline = PricePipeline(FakeMarketDataProvider(bar_count=0))

    with pytest.raises(InsufficientDataError):
        await pipeline.get_prices("NVDA", "1d", "6m")

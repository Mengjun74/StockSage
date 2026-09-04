from datetime import UTC, datetime, timedelta

from app.analytics.price_structure import build_price_structure
from app.providers.base import PriceBar


def test_price_structure_identifies_bullish_trend() -> None:
    bars = [
        PriceBar(
            ticker="AAPL",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            adjusted_close=101 + index,
            volume=1_000_000,
            interval="1d",
            provider="test",
        )
        for index in range(70)
    ]

    structure = build_price_structure(bars)

    assert structure is not None
    assert structure.trend == "bullish"
    assert structure.breakout_state in {"breakout", "near_resistance", "range_bound"}

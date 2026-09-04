from datetime import UTC, datetime, timedelta

from app.analytics.indicators import build_indicator_snapshot
from app.providers.base import PriceBar


def test_build_indicator_snapshot_calculates_core_metrics() -> None:
    bars = [
        PriceBar(
            ticker="NVDA",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            adjusted_close=101 + index,
            volume=1_000_000 + index * 1_000,
            interval="1d",
            provider="test",
        )
        for index in range(60)
    ]

    snapshot = build_indicator_snapshot(bars)

    assert snapshot is not None
    assert snapshot.current_price == 160
    assert snapshot.return_5d is not None
    assert snapshot.sma_20 is not None
    assert snapshot.sma_50 is not None
    assert snapshot.volume_ratio_20d is not None
    assert snapshot.rsi_14 is not None

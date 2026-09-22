"""Guards on how indicators are defined, not merely that they produce a number.

These readings feed the analysis layer, so a value carrying the wrong definition or
the wrong window is worse than no value: it is wrong under a name that looks right.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.indicators import build_indicator_snapshot
from app.providers.base import PriceBar


def make_bars(
    closes: list[float], interval: str = "1d", ticker: str = "TEST", step_days: float | None = None
) -> list[PriceBar]:
    if step_days is not None:
        step = timedelta(days=step_days)
    else:
        step = timedelta(hours=1) if interval == "1h" else timedelta(days=1)
    return [
        PriceBar(
            ticker=ticker,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC) + step * index,
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            adjusted_close=close,
            volume=1_000_000 + index,
            interval=interval,
            provider="test",
        )
        for index, close in enumerate(closes)
    ]


def wilder_rsi(closes: list[float], period: int = 14) -> float:
    """Wilder's RSI written out longhand, independently of the implementation."""
    gains, losses = [], []
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for index in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[index]) / period
        avg_loss = (avg_loss * (period - 1) + losses[index]) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def wilder_atr(bars: list[PriceBar], period: int = 14) -> float:
    ranges = [bars[0].high - bars[0].low]
    for previous, current in zip(bars, bars[1:]):
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    average = sum(ranges[:period]) / period
    for index in range(period, len(ranges)):
        average = (average * (period - 1) + ranges[index]) / period
    return average


CLOSES = [100, 102, 101, 105, 103, 108, 107, 110, 109, 112, 111, 115, 113, 118,
          117, 120, 119, 123, 121, 126, 124, 129, 127, 132, 130, 135, 133, 138,
          136, 141, 139, 144, 142, 147, 145, 150]


def test_rsi_uses_wilder_smoothing() -> None:
    snapshot = build_indicator_snapshot(make_bars(CLOSES))

    assert snapshot is not None
    assert snapshot.rsi_14 == pytest.approx(wilder_rsi(CLOSES), abs=1e-9)


def test_atr_uses_wilder_smoothing() -> None:
    bars = make_bars(CLOSES)
    snapshot = build_indicator_snapshot(bars)

    assert snapshot is not None
    assert snapshot.atr_14 == pytest.approx(wilder_atr(bars), abs=1e-9)


def test_rsi_is_neutral_rather_than_missing_on_a_flat_series() -> None:
    snapshot = build_indicator_snapshot(make_bars([100.0] * 40))

    assert snapshot is not None
    assert snapshot.rsi_14 == 50.0


def test_52w_high_is_absent_when_the_window_is_not_a_year() -> None:
    """A six-month request does not know the 52-week high; it must not invent one."""
    snapshot = build_indicator_snapshot(make_bars([100 + i for i in range(126)]))

    assert snapshot is not None
    assert snapshot.high_52w is None
    assert snapshot.low_52w is None
    assert snapshot.distance_from_52w_high is None
    assert snapshot.high_20d is not None


def test_52w_high_appears_once_the_history_spans_a_year() -> None:
    """Measured by calendar span, not bar count: a 1y request returns ~251 sessions,
    so any fixed count sits on the boundary and mostly misses."""
    closes = [100 + i for i in range(251)]
    bars = make_bars(closes, step_days=1.45)  # 251 bars spread across ~364 days

    snapshot = build_indicator_snapshot(bars)

    assert snapshot is not None
    assert snapshot.high_52w == pytest.approx(max(closes) + 1)
    assert snapshot.low_52w == pytest.approx(min(closes) - 1)


def test_day_windows_are_measured_in_days_on_hourly_bars() -> None:
    """return_1d on hourly bars must span a session, not a single hour."""
    closes = [100 + i for i in range(200)]
    hourly = build_indicator_snapshot(make_bars(closes, interval="1h"))

    assert hourly is not None
    assert hourly.return_1h == pytest.approx(closes[-1] / closes[-2] - 1)
    assert hourly.return_1d == pytest.approx(closes[-1] / closes[-8] - 1)
    assert hourly.return_5d == pytest.approx(closes[-1] / closes[-36] - 1)
    assert hourly.high_20d == pytest.approx(max(closes[-140:]) + 1)


def test_daily_bars_keep_one_bar_per_day() -> None:
    closes = [100 + i for i in range(200)]
    daily = build_indicator_snapshot(make_bars(closes))

    assert daily is not None
    assert daily.return_1h is None
    assert daily.return_1d == pytest.approx(closes[-1] / closes[-2] - 1)
    assert daily.high_20d == pytest.approx(max(closes[-20:]) + 1)

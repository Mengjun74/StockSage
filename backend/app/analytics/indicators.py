import math
from datetime import timedelta

import pandas as pd

from app.providers.base import PriceBar
from app.schemas.prices import IndicatorSnapshot


# Windows named in days have to be expressed in bars. A US regular session yields one
# daily bar or roughly seven hourly ones, so "20d" on an hourly series is 140 bars, not
# 20 -- computing it as 20 would silently report a 20-hour figure under a daily label.
BARS_PER_DAY = {"1d": 1, "1h": 7}

# A 52-week high is a calendar fact, so it is taken over a date range rather than a bar
# count: a one-year request returns about 251 sessions, and any fixed count sits right on
# that boundary and mostly misses.
ONE_YEAR = timedelta(days=365)
# Below this the history is not a year and no 52-week figure is reported.
MIN_YEAR_SPAN = timedelta(days=350)


def bars_to_frame(bars: list[PriceBar]) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "adjusted_close": bar.adjusted_close,
                "volume": bar.volume,
            }
            for bar in bars
        ]
    )
    if frame.empty:
        return frame
    return frame.sort_values("timestamp").reset_index(drop=True)


def build_indicator_snapshot(bars: list[PriceBar]) -> IndicatorSnapshot | None:
    frame = bars_to_frame(bars)
    if frame.empty:
        return None

    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    volume = frame["volume"]
    returns = close.pct_change()

    interval = bars[-1].interval
    bars_per_day = BARS_PER_DAY.get(interval, 1)

    def days(count: int) -> int:
        return count * bars_per_day

    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    bollinger_middle = close.rolling(20).mean()
    bollinger_std = close.rolling(20).std()

    current_price = float(close.iloc[-1])
    high_20d = _last_rolling_value(high.rolling(days(20)).max())
    low_20d = _last_rolling_value(low.rolling(days(20)).min())
    # None unless the history really covers a year: a six-month request does not know
    # the 52-week high, and reporting its six-month high under that name is worse than
    # reporting nothing.
    high_52w, low_52w = _year_extremes(frame)
    volume_avg_20d = _last_rolling_value(volume.rolling(days(20)).mean())

    return IndicatorSnapshot(
        current_price=current_price,
        return_1h=_period_return(close, 1) if interval == "1h" else None,
        return_1d=_period_return(close, days(1)),
        return_5d=_period_return(close, days(5)),
        return_20d=_period_return(close, days(20)),
        volume=int(volume.iloc[-1]) if not pd.isna(volume.iloc[-1]) else None,
        volume_avg_20d=volume_avg_20d,
        volume_ratio_20d=_safe_div(float(volume.iloc[-1]), volume_avg_20d),
        high_20d=high_20d,
        low_20d=low_20d,
        high_52w=high_52w,
        low_52w=low_52w,
        distance_from_20d_high=_distance(current_price, high_20d),
        distance_from_20d_low=_distance(current_price, low_20d),
        distance_from_52w_high=_distance(current_price, high_52w),
        distance_from_52w_low=_distance(current_price, low_52w),
        volatility_5d=_last_rolling_value(returns.rolling(days(5)).std()),
        volatility_20d=_last_rolling_value(returns.rolling(days(20)).std()),
        sma_20=_last_rolling_value(close.rolling(20).mean()),
        sma_50=_last_rolling_value(close.rolling(50).mean()),
        sma_200=_last_rolling_value(close.rolling(200).mean()),
        ema_12=_last_rolling_value(close.ewm(span=12, adjust=False).mean()),
        ema_26=_last_rolling_value(close.ewm(span=26, adjust=False).mean()),
        rsi_14=_calculate_rsi(close, 14),
        macd=_last_rolling_value(macd_line),
        macd_signal=_last_rolling_value(macd_signal),
        macd_histogram=_last_rolling_value(macd_line - macd_signal),
        atr_14=_calculate_atr(high, low, close, 14),
        bollinger_upper=_last_rolling_value(bollinger_middle + 2 * bollinger_std),
        bollinger_middle=_last_rolling_value(bollinger_middle),
        bollinger_lower=_last_rolling_value(bollinger_middle - 2 * bollinger_std),
    )


def _year_extremes(frame: pd.DataFrame) -> tuple[float | None, float | None]:
    timestamps = frame["timestamp"]
    last = timestamps.iloc[-1]
    if last - timestamps.iloc[0] < MIN_YEAR_SPAN:
        return None, None
    window = frame[timestamps >= last - ONE_YEAR]
    return _clean_float(window["high"].max()), _clean_float(window["low"].min())


def _period_return(close: pd.Series, periods: int) -> float | None:
    if len(close) <= periods:
        return None
    return _clean_float((float(close.iloc[-1]) / float(close.iloc[-periods - 1])) - 1)


def _wilder_smooth(values: pd.Series, period: int) -> pd.Series:
    """Wilder's moving average, as RSI and ATR are defined.

    Seeded with the simple mean of the first `period` observations and then run
    recursively. A plain rolling mean is a different average and puts these readings
    visibly out of step with every charting platform.
    """
    clean = values.dropna()
    if len(clean) < period:
        return pd.Series(dtype="float64")
    seeded = clean.iloc[period - 1 :].copy()
    seeded.iloc[0] = float(clean.iloc[:period].mean())
    # ewm(alpha=1/period, adjust=False) from that seed is exactly Wilder's recursion.
    return seeded.ewm(alpha=1 / period, adjust=False).mean()


def _calculate_rsi(close: pd.Series, period: int) -> float | None:
    if len(close) <= period:
        return None
    delta = close.diff()
    gain = _wilder_smooth(delta.clip(lower=0), period)
    loss = _wilder_smooth(-delta.clip(upper=0), period)
    if gain.empty or loss.empty:
        return None

    last_gain, last_loss = float(gain.iloc[-1]), float(loss.iloc[-1])
    if last_loss == 0:
        # No downside in the window: fully overbought, or flat and therefore neutral.
        return 100.0 if last_gain > 0 else 50.0
    return _clean_float(100 - (100 / (1 + last_gain / last_loss)))


def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> float | None:
    if len(close) <= period:
        return None
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _last_rolling_value(_wilder_smooth(true_range, period))


def _last_rolling_value(series: pd.Series) -> float | None:
    value = series.iloc[-1] if not series.empty else None
    return _clean_float(value)


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if denominator in (None, 0):
        return None
    return _clean_float(numerator / denominator)


def _distance(current: float, reference: float | None) -> float | None:
    if reference in (None, 0):
        return None
    return _clean_float((current - reference) / reference)


def _clean_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return None
    return number

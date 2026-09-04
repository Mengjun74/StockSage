import math

import pandas as pd

from app.providers.base import PriceBar
from app.schemas.prices import IndicatorSnapshot


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

    macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    bollinger_middle = close.rolling(20).mean()
    bollinger_std = close.rolling(20).std()

    current_price = float(close.iloc[-1])
    high_20d = _last_rolling_value(high.rolling(20).max())
    low_20d = _last_rolling_value(low.rolling(20).min())
    high_52w = _last_rolling_value(high.rolling(min(252, len(high))).max())
    low_52w = _last_rolling_value(low.rolling(min(252, len(low))).min())
    volume_avg_20d = _last_rolling_value(volume.rolling(20).mean())

    return IndicatorSnapshot(
        current_price=current_price,
        return_1h=_period_return(close, 1) if bars[-1].interval == "1h" else None,
        return_1d=_period_return(close, 1),
        return_5d=_period_return(close, 5),
        return_20d=_period_return(close, 20),
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
        volatility_5d=_last_rolling_value(returns.rolling(5).std()),
        volatility_20d=_last_rolling_value(returns.rolling(20).std()),
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


def _period_return(close: pd.Series, periods: int) -> float | None:
    if len(close) <= periods:
        return None
    return _clean_float((float(close.iloc[-1]) / float(close.iloc[-periods - 1])) - 1)


def _calculate_rsi(close: pd.Series, period: int) -> float | None:
    if len(close) <= period:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100.0 if gain.iloc[-1] > 0 else None
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return _last_rolling_value(rsi)


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
    return _last_rolling_value(true_range.rolling(period).mean())


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

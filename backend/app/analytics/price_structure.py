from app.analytics.indicators import bars_to_frame
from app.providers.base import PriceBar
from app.schemas.prices import PriceStructure


def build_price_structure(bars: list[PriceBar]) -> PriceStructure | None:
    frame = bars_to_frame(bars)
    if frame.empty:
        return None

    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    volume = frame["volume"]

    swing_highs = _local_extrema(high.tolist(), mode="high")[-5:]
    swing_lows = _local_extrema(low.tolist(), mode="low")[-5:]
    current_price = float(close.iloc[-1])

    support_levels = sorted([level for level in swing_lows if level < current_price], reverse=True)[:3]
    resistance_levels = sorted([level for level in swing_highs if level > current_price])[:3]

    trend = "neutral"
    if len(close) >= 50:
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        if current_price > sma_20 > sma_50:
            trend = "bullish"
        elif current_price < sma_20 < sma_50:
            trend = "bearish"

    volume_state = "unknown"
    if len(volume) >= 20:
        average_volume = float(volume.rolling(20).mean().iloc[-1])
        if average_volume > 0:
            ratio = float(volume.iloc[-1]) / average_volume
            if ratio >= 1.25:
                volume_state = "above_average"
            elif ratio <= 0.75:
                volume_state = "below_average"
            else:
                volume_state = "normal"

    breakout_state = "unknown"
    if len(high) >= 20 and len(low) >= 20:
        prior_high = float(high.iloc[-21:-1].max()) if len(high) > 20 else float(high.iloc[:-1].max())
        prior_low = float(low.iloc[-21:-1].min()) if len(low) > 20 else float(low.iloc[:-1].min())
        if current_price > prior_high:
            breakout_state = "breakout"
        elif current_price >= prior_high * 0.98:
            breakout_state = "near_resistance"
        elif current_price <= prior_low * 1.05 and trend == "bullish":
            breakout_state = "pullback"
        else:
            breakout_state = "range_bound"

    return PriceStructure(
        trend=trend,
        support_levels=[round(value, 2) for value in support_levels],
        resistance_levels=[round(value, 2) for value in resistance_levels],
        swing_highs=[round(value, 2) for value in swing_highs],
        swing_lows=[round(value, 2) for value in swing_lows],
        volume_state=volume_state,
        breakout_state=breakout_state,
    )


def _local_extrema(values: list[float], mode: str, radius: int = 2) -> list[float]:
    extrema: list[float] = []
    if len(values) < radius * 2 + 1:
        return extrema
    for index in range(radius, len(values) - radius):
        window = values[index - radius : index + radius + 1]
        value = values[index]
        if mode == "high" and value == max(window):
            extrema.append(float(value))
        if mode == "low" and value == min(window):
            extrema.append(float(value))
    return extrema

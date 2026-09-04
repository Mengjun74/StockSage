from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SupportedInterval = Literal["1h", "1d"]
SupportedPeriod = Literal["1m", "3m", "6m", "1y", "5y"]


class PricePoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None = None
    volume: int


class IndicatorSnapshot(BaseModel):
    current_price: float
    return_1h: float | None = None
    return_1d: float | None = None
    return_5d: float | None = None
    return_20d: float | None = None
    volume: int | None = None
    volume_avg_20d: float | None = None
    volume_ratio_20d: float | None = None
    high_20d: float | None = None
    low_20d: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    distance_from_20d_high: float | None = None
    distance_from_20d_low: float | None = None
    distance_from_52w_high: float | None = None
    distance_from_52w_low: float | None = None
    volatility_5d: float | None = None
    volatility_20d: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    atr_14: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None


class PriceStructure(BaseModel):
    trend: Literal["bullish", "neutral", "bearish"]
    support_levels: list[float]
    resistance_levels: list[float]
    swing_highs: list[float]
    swing_lows: list[float]
    volume_state: Literal["above_average", "normal", "below_average", "unknown"]
    breakout_state: Literal["breakout", "near_resistance", "pullback", "range_bound", "unknown"]


class DataQuality(BaseModel):
    providers_available: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PriceResponse(BaseModel):
    ticker: str
    interval: SupportedInterval
    period: SupportedPeriod
    provider: str
    prices: list[PricePoint]
    snapshot: IndicatorSnapshot | None = None
    price_structure: PriceStructure | None = None
    data_quality: DataQuality


class StockMetadata(BaseModel):
    ticker: str
    valid: bool
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    current_price: float | None = None
    message: str | None = None

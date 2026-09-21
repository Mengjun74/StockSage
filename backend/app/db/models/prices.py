from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PriceRaw(Base):
    __tablename__ = "prices_raw"
    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", "interval", "provider", name="uq_prices_raw_bar"),
        Index("ix_prices_raw_ticker_timestamp", "ticker", "timestamp"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger)
    interval: Mapped[str] = mapped_column(String(8), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="yahoo")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PriceDaily(Base):
    __tablename__ = "prices_daily"
    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", "provider", name="uq_prices_daily_bar"),
        Index("ix_prices_daily_ticker_timestamp", "ticker", "timestamp"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(32), default="yahoo")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PriceHourly(Base):
    __tablename__ = "prices_hourly"
    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", "provider", name="uq_prices_hourly_bar"),
        Index("ix_prices_hourly_ticker_timestamp", "ticker", "timestamp"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger)
    provider: Mapped[str] = mapped_column(String(32), default="yahoo")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MarketSnapshot(Base):
    """Indicators as computed for one (ticker, bar, interval, period) request.

    Interval and period are part of the identity, not metadata: a 1m request cannot
    fill sma_200 and its "52w" high spans a month, so a snapshot is only meaningful
    next to the window it was derived from.
    """

    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", "interval", "period", name="uq_market_snapshots_window"),
        Index("ix_market_snapshots_ticker_timestamp", "ticker", "timestamp"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interval: Mapped[str] = mapped_column(String(8))
    period: Mapped[str] = mapped_column(String(8))
    current_price: Mapped[float] = mapped_column(Float)
    return_1h: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    volume_avg_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_ratio_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_20d_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_20d_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_52w_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_52w_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_20: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema_26: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr_14: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_middle: Mapped[float | None] = mapped_column(Float, nullable=True)
    bollinger_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

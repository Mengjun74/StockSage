import logging
import re
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators import build_indicator_snapshot
from app.analytics.price_structure import build_price_structure
from app.db.models.prices import MarketSnapshot, PriceDaily, PriceHourly, PriceRaw
from app.providers.base import MarketDataProvider, PriceBar
from app.schemas.prices import DataQuality, PricePoint, PriceResponse


logger = logging.getLogger(__name__)
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")


class InvalidTickerError(ValueError):
    pass


class InsufficientDataError(ValueError):
    pass


class PricePipeline:
    def __init__(self, provider: MarketDataProvider) -> None:
        self.provider = provider

    async def get_prices(
        self,
        ticker: str,
        interval: str,
        period: str,
        session: AsyncSession | None = None,
    ) -> PriceResponse:
        normalized_ticker = normalize_ticker(ticker)
        try:
            bars = await self.provider.get_price_history(normalized_ticker, interval, period)
        except Exception as exc:
            logger.exception("market data provider failed", extra={"ticker": normalized_ticker, "provider": self.provider.name})
            return PriceResponse(
                ticker=normalized_ticker,
                interval=interval,
                period=period,
                provider=self.provider.name,
                prices=[],
                data_quality=DataQuality(
                    providers_failed=[self.provider.name],
                    warnings=[f"{self.provider.name} failed: {exc}"],
                ),
            )

        bars = normalize_price_bars(bars)
        if not bars:
            raise InsufficientDataError(f"Not enough historical market data is available for {normalized_ticker}.")

        snapshot = build_indicator_snapshot(bars)
        price_structure = build_price_structure(bars)

        if session is not None:
            await self.persist_prices(session, bars, snapshot)

        return PriceResponse(
            ticker=normalized_ticker,
            interval=interval,
            period=period,
            provider=self.provider.name,
            prices=[
                PricePoint(
                    timestamp=bar.timestamp,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    adjusted_close=bar.adjusted_close,
                    volume=bar.volume,
                )
                for bar in bars
            ],
            snapshot=snapshot,
            price_structure=price_structure,
            data_quality=DataQuality(providers_available=[self.provider.name]),
        )

    async def persist_prices(
        self,
        session: AsyncSession,
        bars: list[PriceBar],
        snapshot: object | None,
    ) -> None:
        ingested_at = datetime.now(UTC)
        raw_rows = [_bar_to_row(bar, ingested_at) for bar in bars]
        await _upsert_rows(session, PriceRaw, raw_rows, ["ticker", "timestamp", "interval", "provider"])

        clean_model = PriceHourly if bars[0].interval == "1h" else PriceDaily
        clean_rows = [_clean_bar_to_row(bar, ingested_at) for bar in bars]
        await _upsert_rows(session, clean_model, clean_rows, ["ticker", "timestamp", "provider"])

        if snapshot is not None:
            snapshot_data = snapshot.model_dump()
            session.add(
                MarketSnapshot(
                    ticker=bars[-1].ticker,
                    timestamp=bars[-1].timestamp,
                    created_at=ingested_at,
                    **snapshot_data,
                )
            )
        await session.commit()


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not TICKER_PATTERN.match(normalized):
        raise InvalidTickerError("Ticker must be 1-15 uppercase letters, numbers, dots, or dashes.")
    return normalized


def normalize_price_bars(bars: list[PriceBar]) -> list[PriceBar]:
    cleaned: list[PriceBar] = []
    seen: set[tuple[str, datetime, str, str]] = set()
    for bar in sorted(bars, key=lambda item: item.timestamp):
        if not _valid_ohlc(bar):
            continue
        timestamp = bar.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        timestamp = timestamp.astimezone(UTC)
        key = (bar.ticker.upper(), timestamp, bar.interval, bar.provider)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(
            PriceBar(
                ticker=bar.ticker.upper(),
                timestamp=timestamp,
                open=round(float(bar.open), 4),
                high=round(float(bar.high), 4),
                low=round(float(bar.low), 4),
                close=round(float(bar.close), 4),
                adjusted_close=None if bar.adjusted_close is None else round(float(bar.adjusted_close), 4),
                volume=max(int(bar.volume), 0),
                interval=bar.interval,
                provider=bar.provider,
            )
        )
    return cleaned


def _valid_ohlc(bar: PriceBar) -> bool:
    return (
        bar.open > 0
        and bar.high > 0
        and bar.low > 0
        and bar.close > 0
        and bar.high >= max(bar.open, bar.close, bar.low)
        and bar.low <= min(bar.open, bar.close, bar.high)
    )


def _bar_to_row(bar: PriceBar, ingested_at: datetime) -> dict[str, object]:
    return {
        "ticker": bar.ticker,
        "timestamp": bar.timestamp,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "adjusted_close": bar.adjusted_close,
        "volume": bar.volume,
        "interval": bar.interval,
        "provider": bar.provider,
        "ingested_at": ingested_at,
    }


def _clean_bar_to_row(bar: PriceBar, ingested_at: datetime) -> dict[str, object]:
    row = _bar_to_row(bar, ingested_at)
    row.pop("interval")
    return row


async def _upsert_rows(
    session: AsyncSession,
    model: type[PriceRaw] | type[PriceDaily] | type[PriceHourly],
    rows: list[dict[str, object]],
    conflict_columns: list[str],
) -> None:
    if not rows:
        return
    statement = insert(model).values(rows)
    update_columns = {
        key: getattr(statement.excluded, key)
        for key in rows[0]
        if key not in {"id", *conflict_columns}
    }
    await session.execute(statement.on_conflict_do_update(index_elements=conflict_columns, set_=update_columns))

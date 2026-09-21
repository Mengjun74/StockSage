import re
from typing import Any

import pytest
from sqlalchemy import BigInteger
from sqlalchemy.dialects import postgresql

from app.analytics.indicators import build_indicator_snapshot
from app.db.models.prices import MarketSnapshot, PriceDaily, PriceHourly, PriceRaw
from app.pipelines.prices import PricePipeline, normalize_price_bars
from tests.fakes import FakeMarketDataProvider


class RecordingSession:
    """Captures the statements persist_prices emits, without needing PostgreSQL."""

    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, statement: Any) -> None:
        self.statements.append(statement)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.commits += 1

    def sql(self) -> list[str]:
        return [str(statement.compile(dialect=postgresql.dialect())) for statement in self.statements]

    def last_row(self) -> dict[str, Any]:
        """Values of the last statement, with the compiler's per-row suffix stripped."""
        params = self.statements[-1].compile(dialect=postgresql.dialect()).params
        return {re.sub(r"_m\d+$", "", key): value for key, value in params.items()}


@pytest.mark.parametrize("model", [PriceRaw, PriceDaily, PriceHourly, MarketSnapshot])
def test_volume_columns_are_big_integers(model: Any) -> None:
    """int4 caps at 2.1B; daily volume passes that on high-float names."""
    assert isinstance(model.__table__.c.volume.type, BigInteger)


async def _persist(period: str = "6m", interval: str = "1d") -> RecordingSession:
    provider = FakeMarketDataProvider(bar_count=60)
    bars = normalize_price_bars(await provider.get_price_history("NVDA", interval, period))
    session = RecordingSession()
    await PricePipeline(provider).persist_prices(session, bars, build_indicator_snapshot(bars), period)
    return session


async def test_snapshot_is_upserted_rather_than_appended() -> None:
    """A plain insert added a duplicate snapshot row on every request."""
    session = await _persist()

    assert session.added == []
    assert session.commits == 1
    snapshot_sql = [query for query in session.sql() if "INSERT INTO market_snapshots" in query]
    assert len(snapshot_sql) == 1
    assert "ON CONFLICT (ticker, timestamp, interval, period) DO UPDATE" in snapshot_sql[0]


async def test_every_statement_is_an_upsert() -> None:
    queries = (await _persist()).sql()

    assert len(queries) == 3
    assert all("ON CONFLICT" in query for query in queries)


async def test_snapshot_records_the_window_it_was_computed_over() -> None:
    row = (await _persist(period="1y")).last_row()

    assert row["ticker"] == "NVDA"
    assert row["interval"] == "1d"
    assert row["period"] == "1y"


async def test_hourly_bars_land_in_the_hourly_table() -> None:
    queries = (await _persist(interval="1h")).sql()

    assert any("INSERT INTO prices_hourly" in query for query in queries)
    assert not any("INSERT INTO prices_daily" in query for query in queries)

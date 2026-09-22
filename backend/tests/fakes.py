from datetime import UTC, datetime, timedelta

from app.providers.base import MarketDataProvider, PriceBar, Quote


class FakeMarketDataProvider(MarketDataProvider):
    """Deterministic provider used in place of Yahoo across the test suite."""

    name = "fake"

    def __init__(self, bar_count: int = 30, failure: Exception | None = None) -> None:
        self.bar_count = bar_count
        self.failure = failure
        self.history_calls: list[tuple[str, str, str]] = []
        self.quote_calls: list[str] = []
        self.quote_price: float | None = 123.45

    async def get_price_history(self, ticker: str, interval: str, period: str) -> list[PriceBar]:
        self.history_calls.append((ticker, interval, period))
        if self.failure is not None:
            raise self.failure
        return [
            PriceBar(
                ticker=ticker,
                timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index),
                open=100 + index,
                high=102 + index,
                low=99 + index,
                close=101 + index,
                adjusted_close=101 + index,
                volume=1_000_000 + index,
                interval=interval,
                provider=self.name,
            )
            for index in range(self.bar_count)
        ]

    async def get_quote(self, ticker: str) -> Quote:
        self.quote_calls.append(ticker)
        if self.failure is not None:
            raise self.failure
        return Quote(
            ticker=ticker,
            current_price=self.quote_price,
            name="Fake Corp",
            exchange="NMS",
            currency="USD",
            provider=self.name,
        )

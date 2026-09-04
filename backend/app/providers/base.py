from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PriceBar:
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int
    interval: str
    provider: str


@dataclass(frozen=True)
class Quote:
    ticker: str
    current_price: float | None
    name: str | None
    exchange: str | None
    currency: str | None
    provider: str


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    async def get_price_history(
        self,
        ticker: str,
        interval: str,
        period: str,
    ) -> list[PriceBar]:
        raise NotImplementedError

    @abstractmethod
    async def get_quote(self, ticker: str) -> Quote:
        raise NotImplementedError

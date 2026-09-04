import asyncio
from datetime import UTC
from typing import Any

import pandas as pd

from app.providers.base import MarketDataProvider, PriceBar, Quote


class YahooMarketDataProvider(MarketDataProvider):
    name = "yahoo"

    async def get_price_history(self, ticker: str, interval: str, period: str) -> list[PriceBar]:
        return await asyncio.to_thread(self._download_history, ticker.upper(), interval, period)

    async def get_quote(self, ticker: str) -> Quote:
        return await asyncio.to_thread(self._quote, ticker.upper())

    def _download_history(self, ticker: str, interval: str, period: str) -> list[PriceBar]:
        import yfinance as yf

        frame = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if frame.empty:
            return []

        frame = self._flatten_columns(frame)
        frame = frame.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adjusted_close",
                "Volume": "volume",
            }
        )
        frame = frame.reset_index()
        time_column = "Datetime" if "Datetime" in frame.columns else "Date"

        bars: list[PriceBar] = []
        for row in frame.to_dict("records"):
            timestamp = pd.Timestamp(row[time_column])
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("America/New_York")
            timestamp = timestamp.tz_convert(UTC)

            if any(pd.isna(row.get(key)) for key in ("open", "high", "low", "close")):
                continue

            volume = row.get("volume")
            adjusted_close = row.get("adjusted_close")
            bars.append(
                PriceBar(
                    ticker=ticker,
                    timestamp=timestamp.to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    adjusted_close=None if pd.isna(adjusted_close) else float(adjusted_close),
                    volume=0 if pd.isna(volume) else int(volume),
                    interval=interval,
                    provider=self.name,
                )
            )
        return bars

    def _quote(self, ticker: str) -> Quote:
        import yfinance as yf

        yf_ticker = yf.Ticker(ticker)
        info: dict[str, Any] = yf_ticker.fast_info or {}
        long_info: dict[str, Any] = {}
        try:
            long_info = yf_ticker.info or {}
        except Exception:
            long_info = {}

        price = info.get("last_price") or long_info.get("currentPrice") or long_info.get("regularMarketPrice")
        return Quote(
            ticker=ticker,
            current_price=None if price is None else float(price),
            name=long_info.get("longName") or long_info.get("shortName"),
            exchange=long_info.get("exchange"),
            currency=long_info.get("currency") or info.get("currency"),
            provider=self.name,
        )

    @staticmethod
    def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
        if isinstance(frame.columns, pd.MultiIndex):
            frame = frame.copy()
            frame.columns = [str(column[0]) for column in frame.columns]
        return frame

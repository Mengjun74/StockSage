import pandas as pd
import pytest

from app.providers.yahoo import YAHOO_PERIODS, YahooMarketDataProvider


def _frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=3, freq="D", name="Date")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [102.0, 103.0, 104.0],
            "Adj Close": [102.0, 103.0, 104.0],
            "Volume": [1_000_000, 1_100_000, 1_200_000],
        },
        index=index,
    )


@pytest.fixture
def captured_download(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_download(ticker: str, **kwargs: object) -> pd.DataFrame:
        captured["ticker"] = ticker
        captured.update(kwargs)
        return _frame()

    monkeypatch.setattr("yfinance.download", fake_download)
    return captured


@pytest.mark.parametrize(("api_period", "yahoo_period"), sorted(YAHOO_PERIODS.items()))
async def test_period_is_translated_to_yahoo_vocabulary(
    captured_download: dict[str, object],
    api_period: str,
    yahoo_period: str,
) -> None:
    """Yahoo reads "6m" as six minutes, so every API period must be sent as "6mo" etc."""
    await YahooMarketDataProvider().get_price_history("nvda", "1d", api_period)

    assert captured_download["period"] == yahoo_period
    assert captured_download["interval"] == "1d"
    assert captured_download["ticker"] == "NVDA"


async def test_bars_keep_the_api_interval_and_are_utc(captured_download: dict[str, object]) -> None:
    bars = await YahooMarketDataProvider().get_price_history("NVDA", "1d", "6m")

    assert len(bars) == 3
    assert {bar.interval for bar in bars} == {"1d"}
    assert {bar.provider for bar in bars} == {"yahoo"}
    assert all(bar.timestamp.utcoffset().total_seconds() == 0 for bar in bars)


async def test_unknown_period_is_rejected_before_calling_yahoo(captured_download: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="no Yahoo equivalent"):
        await YahooMarketDataProvider().get_price_history("NVDA", "1d", "6mo")

    assert captured_download == {}

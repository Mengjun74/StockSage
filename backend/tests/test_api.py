from collections.abc import Callable

import httpx

from tests.fakes import FakeMarketDataProvider


async def test_health_endpoint(make_client: Callable[..., httpx.AsyncClient]) -> None:
    async with make_client() as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_prices_endpoint_returns_bars_and_analytics(make_client: Callable[..., httpx.AsyncClient]) -> None:
    provider = FakeMarketDataProvider(bar_count=60)

    async with make_client(provider) as client:
        response = await client.get("/api/v1/stocks/nvda/prices", params={"interval": "1d", "period": "6m"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["provider"] == "fake"
    assert len(body["prices"]) == 60
    assert body["snapshot"]["sma_50"] is not None
    assert body["price_structure"]["trend"] == "bullish"
    assert body["data_quality"]["providers_available"] == ["fake"]
    assert provider.history_calls == [("NVDA", "1d", "6m")]


async def test_prices_endpoint_defaults_to_daily_six_months(make_client: Callable[..., httpx.AsyncClient]) -> None:
    provider = FakeMarketDataProvider()

    async with make_client(provider) as client:
        response = await client.get("/api/v1/stocks/NVDA/prices")

    assert response.status_code == 200
    assert provider.history_calls == [("NVDA", "1d", "6m")]


async def test_prices_endpoint_rejects_invalid_ticker(make_client: Callable[..., httpx.AsyncClient]) -> None:
    async with make_client(FakeMarketDataProvider()) as client:
        response = await client.get("/api/v1/stocks/nvda;drop/prices")

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "INVALID_TICKER"


async def test_prices_endpoint_reports_empty_history_as_missing(make_client: Callable[..., httpx.AsyncClient]) -> None:
    async with make_client(FakeMarketDataProvider(bar_count=0)) as client:
        response = await client.get("/api/v1/stocks/NVDA/prices")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "INSUFFICIENT_DATA"


async def test_prices_endpoint_surfaces_provider_failure_as_502(make_client: Callable[..., httpx.AsyncClient]) -> None:
    provider = FakeMarketDataProvider(failure=RuntimeError("yahoo rate limited"))

    async with make_client(provider) as client:
        response = await client.get("/api/v1/stocks/NVDA/prices")

    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "PROVIDER_FAILED"


async def test_prices_endpoint_rejects_unsupported_period(make_client: Callable[..., httpx.AsyncClient]) -> None:
    async with make_client(FakeMarketDataProvider()) as client:
        response = await client.get("/api/v1/stocks/NVDA/prices", params={"period": "6mo"})

    assert response.status_code == 422


async def test_stock_metadata_endpoint_returns_quote(make_client: Callable[..., httpx.AsyncClient]) -> None:
    async with make_client(FakeMarketDataProvider()) as client:
        response = await client.get("/api/v1/stocks/nvda")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "ticker": "NVDA",
        "valid": True,
        "name": "Fake Corp",
        "exchange": "NMS",
        "currency": "USD",
        "current_price": 123.45,
        "message": None,
    }


async def test_stock_metadata_endpoint_surfaces_provider_failure_as_502(
    make_client: Callable[..., httpx.AsyncClient],
) -> None:
    async with make_client(FakeMarketDataProvider(failure=RuntimeError("boom"))) as client:
        response = await client.get("/api/v1/stocks/NVDA")

    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "PROVIDER_FAILED"

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_price_pipeline
from app.db.session import get_db_session
from app.pipelines.prices import InsufficientDataError, InvalidTickerError, PricePipeline, normalize_ticker
from app.schemas.prices import PriceResponse, StockMetadata, SupportedInterval, SupportedPeriod


router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}", response_model=StockMetadata)
async def get_stock(
    ticker: str,
    pipeline: Annotated[PricePipeline, Depends(get_price_pipeline)],
) -> StockMetadata:
    try:
        normalized = normalize_ticker(ticker)
        quote = await pipeline.provider.get_quote(normalized)
    except InvalidTickerError as exc:
        raise HTTPException(status_code=400, detail={"error": "INVALID_TICKER", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "PROVIDER_FAILED", "message": "Ticker validation provider failed."},
        ) from exc

    if quote.current_price is None:
        return StockMetadata(ticker=normalized, valid=False, message=f"Ticker {normalized} could not be resolved.")

    return StockMetadata(
        ticker=normalized,
        valid=True,
        name=quote.name,
        exchange=quote.exchange,
        currency=quote.currency,
        current_price=quote.current_price,
    )


@router.get("/{ticker}/prices", response_model=PriceResponse)
async def get_prices(
    ticker: str,
    pipeline: Annotated[PricePipeline, Depends(get_price_pipeline)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    interval: SupportedInterval = Query(default="1d"),
    period: SupportedPeriod = Query(default="6m"),
) -> PriceResponse:
    try:
        return await pipeline.get_prices(ticker=ticker, interval=interval, period=period, session=session)
    except InvalidTickerError as exc:
        raise HTTPException(status_code=400, detail={"error": "INVALID_TICKER", "message": str(exc)}) from exc
    except InsufficientDataError as exc:
        raise HTTPException(status_code=404, detail={"error": "INSUFFICIENT_DATA", "message": str(exc)}) from exc

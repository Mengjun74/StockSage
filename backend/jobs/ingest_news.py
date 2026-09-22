"""Archive news for every ticker with price history.

Analysis runs a few times a day and needs everything published since the last one, so
this is scheduled rather than called on demand -- three runs a day (pre-open, midday,
after the close) covers a position trader.

    python -m jobs.ingest_news            # every ticker already in the database
    python -m jobs.ingest_news NVDA AMD   # just these
"""

import asyncio
import logging
import sys

from sqlalchemy import select

from app.api.dependencies import get_news_pipeline
from app.core.logging import configure_logging
from app.db.models.prices import PriceDaily
from app.db.session import get_sessionmaker
from app.pipelines.prices import normalize_ticker


logger = logging.getLogger(__name__)


async def tracked_tickers(session) -> list[str]:
    result = await session.execute(select(PriceDaily.ticker).distinct().order_by(PriceDaily.ticker))
    return list(result.scalars())


async def run(tickers: list[str]) -> int:
    pipeline = get_news_pipeline()
    total = 0
    async with get_sessionmaker()() as session:
        targets = [normalize_ticker(t) for t in tickers] if tickers else await tracked_tickers(session)
        if not targets:
            logger.info("no tickers to ingest; look at one in the dashboard first")
            return 0
        for ticker in targets:
            count = await pipeline.ingest(session, ticker)
            total += count
            logger.info("ingested news", extra={"ticker": ticker, "articles": count})
    return total


def main() -> None:
    configure_logging()
    total = asyncio.run(run(sys.argv[1:]))
    logger.info("news ingestion finished", extra={"articles": total})


if __name__ == "__main__":
    main()

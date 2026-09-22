import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.news import NewsArticle
from app.providers.news.base import NewsItem, NewsProvider
from app.schemas.news import NewsArticleOut, NewsResponse


logger = logging.getLogger(__name__)


class NewsPipeline:
    def __init__(self, providers: list[NewsProvider]) -> None:
        self.providers = providers

    async def collect(self, ticker: str) -> tuple[list[NewsItem], list[str], list[str]]:
        """Every source is queried concurrently and one failing never sinks the rest:
        SEC being slow should not cost you the headlines."""
        results = await asyncio.gather(
            *(provider.fetch(ticker) for provider in self.providers), return_exceptions=True
        )

        items: list[NewsItem] = []
        available: list[str] = []
        failed: list[str] = []
        for provider, result in zip(self.providers, results):
            if isinstance(result, BaseException):
                logger.warning(
                    "news provider raised", exc_info=result, extra={"ticker": ticker, "provider": provider.name}
                )
                failed.append(provider.name)
                continue
            available.append(provider.name)
            items.extend(result)

        return deduplicate(items), available, failed

    async def ingest(self, session: AsyncSession, ticker: str) -> int:
        """Fetch and archive. Returns how many rows the upsert touched."""
        items, _, _ = await self.collect(ticker)
        if not items:
            return 0

        ingested_at = datetime.now(UTC)
        rows = [
            {
                "ticker": item.ticker,
                "published_at": item.published_at,
                "source": item.source,
                "publisher": item.publisher,
                "title": item.title,
                "summary": item.summary,
                "url": item.url,
                "content_hash": item.content_hash,
                "ingested_at": ingested_at,
            }
            for item in items
        ]
        statement = insert(NewsArticle).values(rows)
        # Seeing a story again must not move its timestamp: published_at is what makes
        # a later review able to ask what was public at the time.
        await session.execute(
            statement.on_conflict_do_nothing(index_elements=["ticker", "content_hash"])
        )
        await session.commit()
        return len(rows)

    async def read(self, session: AsyncSession, ticker: str, days: int) -> NewsResponse:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.ticker == ticker, NewsArticle.published_at >= since)
            .order_by(NewsArticle.published_at.desc())
        )
        return NewsResponse(
            ticker=ticker,
            days=days,
            articles=[
                NewsArticleOut(
                    published_at=row.published_at,
                    source=row.source,
                    publisher=row.publisher,
                    title=row.title,
                    summary=row.summary,
                    url=row.url,
                )
                for row in result.scalars()
            ],
        )


def deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    """One row per story. The same headline reaches us from several feeds, and the
    earliest sighting is the one worth keeping -- it is when the story broke."""
    best: dict[tuple[str, str], NewsItem] = {}
    for item in items:
        # Keyed by ticker as well as story, matching the table: one story can be
        # material to several holdings and must not collapse across them.
        key = (item.ticker, item.content_hash)
        existing = best.get(key)
        if existing is None or item.published_at < existing.published_at:
            best[key] = item
    return sorted(best.values(), key=lambda item: item.published_at, reverse=True)

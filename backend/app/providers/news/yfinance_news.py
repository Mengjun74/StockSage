import asyncio
import logging
from datetime import UTC, datetime

from app.providers.news.base import NewsItem, NewsProvider


logger = logging.getLogger(__name__)


class YfinanceNewsProvider(NewsProvider):
    """Yahoo's curated per-ticker list, reached through the dependency already in use.
    Fewer items than the RSS feed but they carry a summary."""

    name = "yfinance"

    async def fetch(self, ticker: str) -> list[NewsItem]:
        return await asyncio.to_thread(self._fetch, ticker)

    def _fetch(self, ticker: str) -> list[NewsItem]:
        import yfinance as yf

        try:
            raw = yf.Ticker(ticker).news or []
        except Exception:
            logger.warning("yfinance news fetch failed", exc_info=True, extra={"ticker": ticker})
            return []

        items: list[NewsItem] = []
        for entry in raw:
            # Newer yfinance nests the story under "content"; older versions are flat.
            content = entry.get("content") if isinstance(entry.get("content"), dict) else entry
            title = str(content.get("title") or "").strip()
            published = _parse_published(content)
            url = _extract_url(content)
            if not title or published is None or not url:
                continue
            provider = content.get("provider")
            items.append(
                NewsItem(
                    ticker=ticker,
                    published_at=published,
                    source=self.name,
                    title=title,
                    url=url,
                    publisher=(provider or {}).get("displayName") if isinstance(provider, dict) else content.get("publisher"),
                    summary=(str(content.get("summary")).strip() or None) if content.get("summary") else None,
                )
            )
        return items


def _parse_published(content: dict) -> datetime | None:
    raw = content.get("pubDate") or content.get("displayTime")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None
    epoch = content.get("providerPublishTime")
    if isinstance(epoch, (int, float)):
        return datetime.fromtimestamp(epoch, tz=UTC)
    return None


def _extract_url(content: dict) -> str:
    for key in ("canonicalUrl", "clickThroughUrl"):
        value = content.get(key)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
    return str(content.get("link") or "").strip()

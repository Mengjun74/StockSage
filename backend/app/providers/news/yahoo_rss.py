import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from app.providers.news.base import NewsItem, NewsProvider


logger = logging.getLogger(__name__)

FEED_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


class YahooRssNewsProvider(NewsProvider):
    """Yahoo's per-ticker headline feed. No key, no quota, and in practice the best
    signal-to-noise of the free sources."""

    name = "yahoo_rss"

    def __init__(self, user_agent: str, timeout: float = 20.0) -> None:
        # The feed answers httpx's default User-Agent with 404 and anything else
        # with the feed, so this header is required rather than polite.
        self.user_agent = user_agent
        self.timeout = timeout

    async def fetch(self, ticker: str) -> list[NewsItem]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers={"User-Agent": self.user_agent}
            ) as client:
                response = await client.get(FEED_URL.format(ticker=ticker))
                response.raise_for_status()
                body = response.text
        except Exception:
            logger.warning("yahoo rss fetch failed", exc_info=True, extra={"ticker": ticker})
            return []

        return await asyncio.to_thread(self._parse, ticker, body)

    def _parse(self, ticker: str, body: str) -> list[NewsItem]:
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            logger.warning("yahoo rss returned unparseable xml", extra={"ticker": ticker})
            return []

        items: list[NewsItem] = []
        for element in root.findall(".//item"):
            title = (element.findtext("title") or "").strip()
            link = (element.findtext("link") or "").strip()
            if not title or not link:
                continue
            published = _parse_rfc822(element.findtext("pubDate"))
            if published is None:
                continue
            items.append(
                NewsItem(
                    ticker=ticker,
                    published_at=published,
                    source=self.name,
                    title=title,
                    url=link,
                    publisher=(element.findtext("source") or "").strip() or None,
                    summary=(element.findtext("description") or "").strip() or None,
                )
            )
        return items


def _parse_rfc822(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)

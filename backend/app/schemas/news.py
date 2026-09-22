from datetime import datetime

from pydantic import BaseModel


class NewsArticleOut(BaseModel):
    published_at: datetime
    source: str
    publisher: str | None = None
    title: str
    summary: str | None = None
    url: str


class NewsResponse(BaseModel):
    ticker: str
    days: int
    articles: list[NewsArticleOut]
    sources_available: list[str] = []
    sources_failed: list[str] = []

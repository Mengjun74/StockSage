from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewsArticle(Base):
    """One story about one ticker, kept rather than fetched on demand.

    Analysis runs a few times a day and has to see everything published since the last
    one, so the feed is archived instead of read live. Keeping published_at is what
    later makes evaluation honest: reviewing a past call means asking what was already
    public when it was made, and a live feed can only answer what is public now.
    """

    __tablename__ = "news_articles"
    __table_args__ = (
        # One row per story per ticker: the same headline reaches us from several feeds.
        UniqueConstraint("ticker", "content_hash", name="uq_news_articles_story"),
        Index("ix_news_articles_ticker_published", "ticker", "published_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(32))
    publisher: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

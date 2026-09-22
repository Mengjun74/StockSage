"""create news_articles

Revision ID: 0003_news_articles
Revises: 0002_volume_bigint_snapshot_key
Create Date: 2026-09-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_news_articles"
down_revision: str | None = "0002_volume_bigint_snapshot_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("publisher", sa.String(length=128), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_news_articles_ticker", "news_articles", ["ticker"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])
    op.create_index("ix_news_articles_ticker_published", "news_articles", ["ticker", "published_at"])
    op.create_unique_constraint("uq_news_articles_story", "news_articles", ["ticker", "content_hash"])


def downgrade() -> None:
    op.drop_table("news_articles")

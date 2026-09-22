"""create analyses

Revision ID: 0004_analyses
Revises: 0003_news_articles
Create Date: 2026-09-22 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_analyses"
down_revision: str | None = "0003_news_articles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("price_at_analysis", sa.Float(), nullable=False),
        sa.Column("entry_label", sa.String(length=32), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("target_label", sa.String(length=32), nullable=False),
        sa.Column("target_price", sa.Float(), nullable=False),
        sa.Column("stop_label", sa.String(length=32), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=False),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("invalidation", sa.Text(), nullable=False),
        sa.Column("disagreement", sa.Text(), nullable=False),
        sa.Column("bull_strength", sa.String(length=16), nullable=False),
        sa.Column("bear_strength", sa.String(length=16), nullable=False),
        sa.Column("bull_case", postgresql.JSONB(), nullable=False),
        sa.Column("bear_case", postgresql.JSONB(), nullable=False),
        sa.Column("context_snapshot", sa.Text(), nullable=False),
        sa.Column("articles_considered", sa.Integer(), nullable=False),
        sa.Column("evaluated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_analyses_ticker", "analyses", ["ticker"])
    op.create_index("ix_analyses_created_at", "analyses", ["created_at"])
    op.create_index("ix_analyses_ticker_created", "analyses", ["ticker", "created_at"])


def downgrade() -> None:
    op.drop_table("analyses")

"""create price tables

Revision ID: 0001_create_price_tables
Revises:
Create Date: 2026-09-03 23:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_price_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_price_table("prices_raw", include_interval=True)
    _create_price_table("prices_daily", include_interval=False)
    _create_price_table("prices_hourly", include_interval=False)

    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=False),
        sa.Column("return_1h", sa.Float(), nullable=True),
        sa.Column("return_1d", sa.Float(), nullable=True),
        sa.Column("return_5d", sa.Float(), nullable=True),
        sa.Column("return_20d", sa.Float(), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("volume_avg_20d", sa.Float(), nullable=True),
        sa.Column("volume_ratio_20d", sa.Float(), nullable=True),
        sa.Column("high_20d", sa.Float(), nullable=True),
        sa.Column("low_20d", sa.Float(), nullable=True),
        sa.Column("high_52w", sa.Float(), nullable=True),
        sa.Column("low_52w", sa.Float(), nullable=True),
        sa.Column("distance_from_20d_high", sa.Float(), nullable=True),
        sa.Column("distance_from_20d_low", sa.Float(), nullable=True),
        sa.Column("distance_from_52w_high", sa.Float(), nullable=True),
        sa.Column("distance_from_52w_low", sa.Float(), nullable=True),
        sa.Column("volatility_5d", sa.Float(), nullable=True),
        sa.Column("volatility_20d", sa.Float(), nullable=True),
        sa.Column("sma_20", sa.Float(), nullable=True),
        sa.Column("sma_50", sa.Float(), nullable=True),
        sa.Column("sma_200", sa.Float(), nullable=True),
        sa.Column("ema_12", sa.Float(), nullable=True),
        sa.Column("ema_26", sa.Float(), nullable=True),
        sa.Column("rsi_14", sa.Float(), nullable=True),
        sa.Column("macd", sa.Float(), nullable=True),
        sa.Column("macd_signal", sa.Float(), nullable=True),
        sa.Column("macd_histogram", sa.Float(), nullable=True),
        sa.Column("atr_14", sa.Float(), nullable=True),
        sa.Column("bollinger_upper", sa.Float(), nullable=True),
        sa.Column("bollinger_middle", sa.Float(), nullable=True),
        sa.Column("bollinger_lower", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_snapshots_ticker", "market_snapshots", ["ticker"])
    op.create_index("ix_market_snapshots_timestamp", "market_snapshots", ["timestamp"])
    op.create_index("ix_market_snapshots_ticker_timestamp", "market_snapshots", ["ticker", "timestamp"])


def downgrade() -> None:
    op.drop_table("market_snapshots")
    op.drop_table("prices_hourly")
    op.drop_table("prices_daily")
    op.drop_table("prices_raw")


def _create_price_table(name: str, include_interval: bool) -> None:
    columns = [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("adjusted_close", sa.Float(), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=False),
    ]
    if include_interval:
        columns.append(sa.Column("interval", sa.String(length=8), nullable=False))
    columns.extend(
        [
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        ]
    )
    op.create_table(name, *columns)
    op.create_index(f"ix_{name}_ticker", name, ["ticker"])
    op.create_index(f"ix_{name}_timestamp", name, ["timestamp"])
    if include_interval:
        op.create_index(f"ix_{name}_interval", name, ["interval"])
        op.create_unique_constraint(f"uq_{name}_bar", name, ["ticker", "timestamp", "interval", "provider"])
    else:
        op.create_unique_constraint(f"uq_{name}_bar", name, ["ticker", "timestamp", "provider"])
    op.create_index(f"ix_{name}_ticker_timestamp", name, ["ticker", "timestamp"])

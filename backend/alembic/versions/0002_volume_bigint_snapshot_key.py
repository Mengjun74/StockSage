"""widen volume columns and key snapshots by window

Revision ID: 0002_volume_bigint_snapshot_key
Revises: 0001_create_price_tables
Create Date: 2026-09-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_volume_bigint_snapshot_key"
down_revision: str | None = "0001_create_price_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRICE_TABLES = ("prices_raw", "prices_daily", "prices_hourly")

# Legacy snapshots predate these columns and cannot be attributed to a window. They were
# produced by the endpoint defaults, which is the only request shape that existed.
LEGACY_INTERVAL = "1d"
LEGACY_PERIOD = "6m"


def upgrade() -> None:
    # int4 tops out at 2,147,483,647; daily volume passes that on high-float names.
    for table in PRICE_TABLES:
        op.alter_column(table, "volume", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column(
        "market_snapshots", "volume", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=True
    )

    op.add_column(
        "market_snapshots",
        sa.Column("interval", sa.String(length=8), nullable=False, server_default=LEGACY_INTERVAL),
    )
    op.add_column(
        "market_snapshots",
        sa.Column("period", sa.String(length=8), nullable=False, server_default=LEGACY_PERIOD),
    )
    # Backfilled only; new rows must state their own window.
    op.alter_column("market_snapshots", "interval", server_default=None)
    op.alter_column("market_snapshots", "period", server_default=None)

    # Every request appended a row, so the table cannot take the constraint as-is.
    # Keep the most recently computed row per window.
    op.execute(
        """
        DELETE FROM market_snapshots AS a
        USING market_snapshots AS b
        WHERE a.ticker = b.ticker
          AND a.timestamp = b.timestamp
          AND a."interval" = b."interval"
          AND a.period = b.period
          AND (a.created_at, a.id) < (b.created_at, b.id)
        """
    )
    op.create_unique_constraint(
        "uq_market_snapshots_window", "market_snapshots", ["ticker", "timestamp", "interval", "period"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_market_snapshots_window", "market_snapshots", type_="unique")
    op.drop_column("market_snapshots", "period")
    op.drop_column("market_snapshots", "interval")

    op.alter_column(
        "market_snapshots", "volume", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=True
    )
    for table in PRICE_TABLES:
        op.alter_column(table, "volume", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)

"""create analysis_outcomes

Revision ID: 0005_analysis_outcomes
Revises: 0004_analyses
Create Date: 2026-09-22 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_analysis_outcomes"
down_revision: str | None = "0004_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method_version", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("entry_filled", sa.Boolean(), nullable=False),
        sa.Column("entry_filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("exit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_pct", sa.Float(), nullable=True),
        sa.Column("max_favorable_pct", sa.Float(), nullable=True),
        sa.Column("max_adverse_pct", sa.Float(), nullable=True),
        sa.Column("bars_evaluated", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("bull_strength", sa.String(length=16), nullable=False),
        sa.Column("bear_strength", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_analysis_outcomes_analysis_id", "analysis_outcomes", ["analysis_id"])
    op.create_index("ix_analysis_outcomes_ticker", "analysis_outcomes", ["ticker"])
    op.create_index("ix_analysis_outcomes_ticker_outcome", "analysis_outcomes", ["ticker", "outcome"])
    # Re-scoring with an improved method adds a row rather than overwriting one.
    op.create_unique_constraint(
        "uq_analysis_outcomes_method", "analysis_outcomes", ["analysis_id", "method_version"]
    )


def downgrade() -> None:
    op.drop_table("analysis_outcomes")

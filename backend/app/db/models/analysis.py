from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Analysis(Base):
    """One completed run: what the agents saw, what each argued, and what was decided.

    Rows are append-only. Scoring a past call means comparing it to what the market
    did afterwards, which is only possible if the call and the evidence behind it were
    written down at the time -- including the losing side's case, which is worth
    reading precisely when the call went wrong.
    """

    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_ticker_created", "ticker", "created_at"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    model: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))

    action: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(16))
    horizon_days: Mapped[int] = mapped_column(Integer)

    price_at_analysis: Mapped[float] = mapped_column(Float)
    entry_label: Mapped[str] = mapped_column(String(32))
    entry_price: Mapped[float] = mapped_column(Float)
    target_label: Mapped[str] = mapped_column(String(32))
    target_price: Mapped[float] = mapped_column(Float)
    stop_label: Mapped[str] = mapped_column(String(32))
    stop_price: Mapped[float] = mapped_column(Float)
    risk_reward: Mapped[float | None] = mapped_column(Float, nullable=True)

    reasoning: Mapped[str] = mapped_column(Text)
    invalidation: Mapped[str] = mapped_column(Text)
    disagreement: Mapped[str] = mapped_column(Text)

    bull_strength: Mapped[str] = mapped_column(String(16))
    bear_strength: Mapped[str] = mapped_column(String(16))
    bull_case: Mapped[dict] = mapped_column(JSONB)
    bear_case: Mapped[dict] = mapped_column(JSONB)
    # The evidence exactly as the agents received it, so a review can ask what was
    # known at the time instead of what is known now.
    context_snapshot: Mapped[str] = mapped_column(Text)
    articles_considered: Mapped[int] = mapped_column(Integer)

    evaluated: Mapped[bool] = mapped_column(Boolean, default=False)

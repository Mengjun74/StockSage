import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.evaluation import METHOD_VERSION, TRADE_ACTIONS, Call, evaluate
from app.db.models.analysis import Analysis, AnalysisOutcome
from app.db.models.prices import PriceDaily
from app.providers.base import PriceBar
from app.schemas.evaluation import OutcomeCounts, PerformanceReport, Segment


logger = logging.getLogger(__name__)


class EvaluationPipeline:
    async def due(self, session: AsyncSession) -> list[Analysis]:
        """Calls whose horizon has run out and that this method has not yet scored."""
        already = select(AnalysisOutcome.analysis_id).where(
            AnalysisOutcome.method_version == METHOD_VERSION
        )
        rows = (await session.execute(select(Analysis).where(Analysis.id.notin_(already)))).scalars()
        now = datetime.now(UTC)
        return [a for a in rows if a.created_at + timedelta(days=a.horizon_days) <= now]

    async def score(self, session: AsyncSession, analysis: Analysis) -> AnalysisOutcome:
        bars = await self._bars(session, analysis)
        result = evaluate(
            Call(
                action=analysis.action,
                entry_label=analysis.entry_label,
                entry_price=analysis.entry_price,
                target_price=analysis.target_price,
                stop_price=analysis.stop_price,
                price_at_analysis=analysis.price_at_analysis,
            ),
            bars,
        )
        outcome = AnalysisOutcome(
            analysis_id=analysis.id,
            ticker=analysis.ticker,
            evaluated_at=datetime.now(UTC),
            method_version=METHOD_VERSION,
            outcome=result.outcome,
            entry_filled=result.entry_filled,
            entry_filled_at=result.entry_filled_at,
            exit_price=result.exit_price,
            exit_at=result.exit_at,
            return_pct=result.return_pct,
            max_favorable_pct=result.max_favorable_pct,
            max_adverse_pct=result.max_adverse_pct,
            bars_evaluated=result.bars_evaluated,
            action=analysis.action,
            confidence=analysis.confidence,
            bull_strength=analysis.bull_strength,
            bear_strength=analysis.bear_strength,
        )
        session.add(outcome)
        analysis.evaluated = True
        return outcome

    async def run(self, session: AsyncSession) -> list[AnalysisOutcome]:
        outcomes = [await self.score(session, analysis) for analysis in await self.due(session)]
        if outcomes:
            await session.commit()
        return outcomes

    async def _bars(self, session: AsyncSession, analysis: Analysis) -> list[PriceBar]:
        """Bars strictly after the call, up to its horizon. Stored when the call was
        made, so scoring needs no network and cannot be contaminated by later revisions."""
        end = analysis.created_at + timedelta(days=analysis.horizon_days)
        rows = await session.execute(
            select(PriceDaily)
            .where(
                PriceDaily.ticker == analysis.ticker,
                PriceDaily.timestamp > analysis.created_at,
                PriceDaily.timestamp <= end,
            )
            .order_by(PriceDaily.timestamp)
        )
        return [
            PriceBar(
                ticker=row.ticker,
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                adjusted_close=row.adjusted_close,
                volume=row.volume,
                interval="1d",
                provider=row.provider,
            )
            for row in rows.scalars()
        ]

    async def report(self, session: AsyncSession) -> PerformanceReport:
        rows = list(
            (
                await session.execute(
                    select(AnalysisOutcome).where(AnalysisOutcome.method_version == METHOD_VERSION)
                )
            ).scalars()
        )
        trades = [r for r in rows if r.action in TRADE_ACTIONS and r.entry_filled]
        counts = OutcomeCounts()
        for row in rows:
            setattr(counts, row.outcome, getattr(counts, row.outcome, 0) + 1)

        return PerformanceReport(
            method_version=METHOD_VERSION,
            analyses_scored=len(rows),
            trades_taken=len(trades),
            counts=counts,
            hit_rate=_hit_rate(trades),
            average_return_pct=_average([r.return_pct for r in trades]),
            # The hypothesis worth testing: does the two sides agreeing predict anything?
            by_agreement=[
                _segment("both sides agree", [r for r in trades if _agrees(r)]),
                _segment("sides disagree", [r for r in trades if not _agrees(r)]),
            ],
            by_confidence=[
                _segment(level, [r for r in trades if r.confidence == level])
                for level in ("high", "medium", "low")
            ],
        )


def _agrees(row: AnalysisOutcome) -> bool:
    """One side clearly outweighing the other. Both strong or both moderate is a
    genuinely balanced call, not an agreement."""
    order = {"weak": 0, "moderate": 1, "strong": 2}
    return order.get(row.bull_strength, 0) != order.get(row.bear_strength, 0)


def _segment(label: str, rows: list[AnalysisOutcome]) -> Segment:
    return Segment(
        label=label,
        trades=len(rows),
        hit_rate=_hit_rate(rows),
        average_return_pct=_average([r.return_pct for r in rows]),
        average_max_adverse_pct=_average([r.max_adverse_pct for r in rows]),
    )


def _hit_rate(rows: list[AnalysisOutcome]) -> float | None:
    decided = [r for r in rows if r.outcome in {"target_hit", "stop_hit"}]
    if not decided:
        return None
    return round(sum(1 for r in decided if r.outcome == "target_hit") / len(decided), 4)


def _average(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 6)

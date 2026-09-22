import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.agents import UnknownLevelError, adjudicate, argue_both_sides
from app.analysis.context import build_context
from app.analysis.levels import build_candidate_levels
from app.db.models.analysis import Analysis
from app.llm.gemini import GeminiClient
from app.pipelines.news import NewsPipeline
from app.pipelines.prices import InsufficientDataError, PricePipeline, normalize_ticker
from app.schemas.analysis import AnalysisResponse, CaseOut, LevelOut

logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-09-22.1"


class AnalysisError(RuntimeError):
    pass


class AnalysisPipeline:
    def __init__(
        self,
        prices: PricePipeline,
        news: NewsPipeline,
        client: GeminiClient,
        news_days: int,
        filing_days: int,
    ) -> None:
        self.prices = prices
        self.news = news
        self.client = client
        self.news_days = news_days
        self.filing_days = filing_days

    async def analyse(self, session: AsyncSession, ticker: str, interval: str = "1d", period: str = "1y") -> AnalysisResponse:
        normalized = normalize_ticker(ticker)

        # A year by default: the shorter windows cannot fill sma_200 or a 52-week range,
        # and the agents should not have to reason around holes we chose to leave.
        prices = await self.prices.get_prices(normalized, interval, period, session)
        if prices.snapshot is None:
            raise InsufficientDataError(f"No indicators could be computed for {normalized}.")

        levels = build_candidate_levels(prices.snapshot, prices.price_structure)
        if levels is None or not levels.targets or not levels.stops:
            raise AnalysisError(
                f"No candidate price levels could be derived for {normalized}; "
                "there is nothing for the agents to choose between."
            )

        news = await self.news.read(session, normalized, self.news_days, self.filing_days)
        context = build_context(normalized, prices.snapshot, prices.price_structure, news.articles, levels)

        bull, bear = await argue_both_sides(self.client, context)
        try:
            verdict = await adjudicate(self.client, context, bull, bear)
        except UnknownLevelError as exc:
            logger.warning("judge named an unknown level", extra={"ticker": normalized})
            raise AnalysisError(str(exc)) from exc

        created_at = datetime.now(UTC)
        session.add(
            Analysis(
                ticker=normalized,
                created_at=created_at,
                model=self.client.model,
                prompt_version=PROMPT_VERSION,
                action=verdict.action,
                confidence=verdict.confidence,
                horizon_days=verdict.horizon_days,
                price_at_analysis=prices.snapshot.current_price,
                entry_label=verdict.entry.label,
                entry_price=verdict.entry.price,
                target_label=verdict.target.label,
                target_price=verdict.target.price,
                stop_label=verdict.stop.label,
                stop_price=verdict.stop.price,
                risk_reward=verdict.risk_reward,
                reasoning=verdict.reasoning,
                invalidation=verdict.invalidation,
                disagreement=verdict.disagreement,
                bull_strength=bull.case_strength,
                bear_strength=bear.case_strength,
                bull_case=_case_json(bull),
                bear_case=_case_json(bear),
                context_snapshot=context.render(),
                articles_considered=len(news.articles),
            )
        )
        await session.commit()

        return AnalysisResponse(
            ticker=normalized,
            created_at=created_at,
            model=self.client.model,
            price_at_analysis=prices.snapshot.current_price,
            action=verdict.action,
            confidence=verdict.confidence,
            horizon_days=verdict.horizon_days,
            entry=_level_out(verdict.entry),
            target=_level_out(verdict.target),
            stop=_level_out(verdict.stop),
            risk_reward=verdict.risk_reward,
            reasoning=verdict.reasoning,
            invalidation=verdict.invalidation,
            disagreement=verdict.disagreement,
            bull=_case_out(bull),
            bear=_case_out(bear),
            articles_considered=len(news.articles),
        )


def _case_json(case) -> dict:
    return {
        "case_strength": case.case_strength,
        "summary": case.summary,
        "points": case.points,
        "strongest_counterpoint": case.strongest_counterpoint,
    }


def _case_out(case) -> CaseOut:
    return CaseOut(
        side=case.side,
        case_strength=case.case_strength,
        summary=case.summary,
        points=[
            {"claim": str(p.get("claim", "")), "evidence": str(p.get("evidence", ""))} for p in case.points
        ],
        strongest_counterpoint=case.strongest_counterpoint,
    )


def _level_out(level) -> LevelOut:
    return LevelOut(label=level.label, price=level.price, basis=level.basis)

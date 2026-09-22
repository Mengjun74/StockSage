"""The three agents and the rule that the judge cannot invent a price."""

import asyncio
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.analysis.context import AnalysisContext
from app.analysis.levels import CandidateLevels, PriceLevel, risk_reward
from app.analysis.schemas import CASE_SCHEMA, VERDICT_SCHEMA
from app.llm.gemini import GeminiClient


logger = logging.getLogger(__name__)

PROMPTS = Path(__file__).parent / "prompts"


@lru_cache
def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


@dataclass(frozen=True)
class Case:
    side: str
    case_strength: str
    summary: str
    points: list[dict]
    strongest_counterpoint: str
    filings_assessment: str


@dataclass(frozen=True)
class Verdict:
    action: str
    confidence: str
    horizon_days: int
    entry: PriceLevel
    target: PriceLevel
    stop: PriceLevel
    risk_reward: float | None
    reasoning: str
    invalidation: str
    disagreement: str


class UnknownLevelError(ValueError):
    """The judge named a level that is not on the candidate list."""


async def argue_both_sides(client: GeminiClient, context: AnalysisContext) -> tuple[Case, Case]:
    """Both sides run against the same evidence, and concurrently, so neither is
    written in reaction to the other's wording."""
    rendered = context.render()
    bull, bear = await asyncio.gather(
        _argue(client, "bull", rendered),
        _argue(client, "bear", rendered),
    )
    return bull, bear


async def _argue(client: GeminiClient, side: str, rendered: str) -> Case:
    prompt = f"{_prompt('shared')}\n\n{_prompt(side)}\n\n{_prompt('filings')}\n\n---\n\n{rendered}"
    data = await client.generate_json(prompt, CASE_SCHEMA)
    return Case(
        side=side,
        case_strength=str(data.get("case_strength", "weak")),
        summary=str(data.get("summary", "")),
        points=list(data.get("points", [])),
        strongest_counterpoint=str(data.get("strongest_counterpoint", "")),
        filings_assessment=str(data.get("filings_assessment", "")),
    )


async def adjudicate(
    client: GeminiClient, context: AnalysisContext, bull: Case, bear: Case
) -> Verdict:
    prompt = (
        f"{_prompt('shared')}\n\n{_prompt('judge')}\n\n{_prompt('filings')}\n\n---\n\n{context.render()}\n\n"
        f"## The case for\n{_render_case(bull)}\n\n## The case against\n{_render_case(bear)}"
    )
    data = await client.generate_json(prompt, VERDICT_SCHEMA, temperature=0.2)
    return build_verdict(data, context.levels)


def build_verdict(data: dict, levels: CandidateLevels) -> Verdict:
    """Resolves the judge's labels against the candidate list.

    An unknown label is rejected rather than coerced: the whole point of labels is that
    the numbers stay reproducible, and quietly substituting a nearby level would defeat
    that while looking like it worked.
    """
    chosen = {}
    for field in ("entry", "target", "stop"):
        label = str(data.get(f"{field}_label", ""))
        level = levels.resolve(label)
        if level is None:
            raise UnknownLevelError(
                f"judge chose {field} level {label!r}, which is not a candidate "
                f"({sorted(levels.by_label())})"
            )
        chosen[field] = level

    return Verdict(
        action=str(data.get("action", "avoid")),
        confidence=str(data.get("confidence", "low")),
        horizon_days=int(data.get("horizon_days", 0)),
        entry=chosen["entry"],
        target=chosen["target"],
        stop=chosen["stop"],
        # Arithmetic stays out of the model's hands.
        risk_reward=risk_reward(chosen["entry"].price, chosen["target"].price, chosen["stop"].price),
        reasoning=str(data.get("reasoning", "")),
        invalidation=str(data.get("invalidation", "")),
        disagreement=str(data.get("disagreement", "")),
    )


def _render_case(case: Case) -> str:
    points = "\n".join(
        f"- {point.get('claim', '')}\n    evidence: {point.get('evidence', '')}" for point in case.points
    )
    return (
        f"Strength: {case.case_strength}\n{case.summary}\n{points}\n"
        f"On the SEC filings: {case.filings_assessment}\n"
        f"Strongest point against this case: {case.strongest_counterpoint}"
    )

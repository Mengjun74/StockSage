"""Score past calls against what the market did, and print how the tool is doing.

No model and no network: the bars were stored when each call was made. Run it daily;
a call is only picked up once its horizon has passed.

    python -m jobs.evaluate_predictions
"""

import asyncio
import logging

from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.pipelines.evaluation import EvaluationPipeline


logger = logging.getLogger(__name__)


async def run() -> None:
    pipeline = EvaluationPipeline()
    async with get_sessionmaker()() as session:
        scored = await pipeline.run(session)
        for outcome in scored:
            logger.info(
                "scored call",
                extra={"ticker": outcome.ticker, "outcome": outcome.outcome},
            )
        report = await pipeline.report(session)

    print(f"\nMethod {report.method_version}")
    print(f"Calls scored: {report.analyses_scored}   trades actually taken: {report.trades_taken}")
    print(f"Outcomes: {report.counts.model_dump()}")
    print(f"Hit rate: {_show(report.hit_rate)}   average return: {_pct(report.average_return_pct)}")

    for title, segments in (("By agreement", report.by_agreement), ("By confidence", report.by_confidence)):
        print(f"\n{title}")
        for segment in segments:
            print(
                f"  {segment.label:<18} n={segment.trades:<4} hit={_show(segment.hit_rate):<8}"
                f" avg={_pct(segment.average_return_pct):<9} worst drawdown={_pct(segment.average_max_adverse_pct)}"
            )
    print(f"\n{report.caveat}")


def _show(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:+.2f}%"


def main() -> None:
    configure_logging()
    asyncio.run(run())


if __name__ == "__main__":
    main()

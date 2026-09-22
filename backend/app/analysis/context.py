"""Assembles what every agent sees. Deterministic: no model is involved.

All three agents receive this same block. Splitting the evidence between them by
source would hide exactly the interactions that matter -- that today's breakout came
on an 8-K, or that the good headline landed straight into resistance.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.analysis.levels import CandidateLevels
from app.pipelines.news import FILINGS_SOURCE
from app.schemas.news import NewsArticleOut
from app.schemas.prices import IndicatorSnapshot, PriceStructure


MAX_ARTICLES = 25
MAX_FILINGS = 10
MAX_SUMMARY_CHARS = 280


@dataclass(frozen=True)
class AnalysisContext:
    ticker: str
    as_of: datetime
    snapshot: IndicatorSnapshot
    structure: PriceStructure | None
    articles: list[NewsArticleOut]
    levels: CandidateLevels

    def render(self) -> str:
        return "\n\n".join(
            [
                f"# {self.ticker} as of {self.as_of.isoformat()}",
                self._indicators(),
                self._structure(),
                self._news(),
                self._filings(),
                self._levels(),
            ]
        )

    def _indicators(self) -> str:
        s = self.snapshot
        rows = [
            ("Current price", s.current_price),
            ("Return 1d / 5d / 20d", _pcts(s.return_1d, s.return_5d, s.return_20d)),
            ("SMA 20 / 50 / 200", _nums(s.sma_20, s.sma_50, s.sma_200)),
            ("RSI(14)", s.rsi_14),
            ("MACD / signal / hist", _nums(s.macd, s.macd_signal, s.macd_histogram)),
            ("ATR(14)", s.atr_14),
            ("Bollinger low / mid / high", _nums(s.bollinger_lower, s.bollinger_middle, s.bollinger_upper)),
            ("20d high / low", _nums(s.high_20d, s.low_20d)),
            ("52w high / low", _nums(s.high_52w, s.low_52w)),
            ("Volume vs 20d average", s.volume_ratio_20d),
            ("Volatility 5d / 20d", _pcts(s.volatility_5d, s.volatility_20d)),
        ]
        body = "\n".join(f"- {label}: {_show(value)}" for label, value in rows)
        return (
            "## Indicators\n"
            "RSI and ATR use Wilder's smoothing. A blank 52-week figure means the history "
            "is shorter than a year, not that the level is unknown to the market.\n" + body
        )

    def _structure(self) -> str:
        if self.structure is None:
            return "## Price structure\nUnavailable."
        p = self.structure
        return (
            "## Price structure\n"
            f"- Trend: {p.trend}\n"
            f"- Setup: {p.breakout_state}\n"
            f"- Volume state: {p.volume_state}\n"
            f"- Support: {_nums(*p.support_levels) or 'none below'}\n"
            f"- Resistance: {_nums(*p.resistance_levels) or 'none above'}"
        )

    @property
    def headlines(self) -> list[NewsArticleOut]:
        return [a for a in self.articles if a.source != FILINGS_SOURCE]

    @property
    def filings(self) -> list[NewsArticleOut]:
        return [a for a in self.articles if a.source == FILINGS_SOURCE]

    def _filings(self) -> str:
        if not self.filings:
            return "## SEC filings\nNone in the window."
        lines = [
            f"- [{f.published_at.date().isoformat()}] {f.title}"
            + (f"\n    {f.summary}" if f.summary else "")
            for f in self.filings[:MAX_FILINGS]
        ]
        header = "## SEC filings\nOfficial and dated. Item codes say what kind of "
        header += "event an 8-K reports.\n"
        return header + "\n".join(lines)

    def _news(self) -> str:
        if not self.headlines:
            return (
                "## News\nNothing published in the window. This is the ordinary state for "
                "most tickers on most days and is not itself a signal."
            )
        lines = []
        for article in self.headlines[:MAX_ARTICLES]:
            summary = (article.summary or "").strip().replace("\n", " ")
            if len(summary) > MAX_SUMMARY_CHARS:
                summary = summary[:MAX_SUMMARY_CHARS].rstrip() + "..."
            source = article.publisher or article.source
            lines.append(
                f"- [{article.published_at.date().isoformat()}] ({source}) {article.title}"
                + (f"\n    {summary}" if summary else "")
            )
        return "## News\nCite these by headline and date.\n" + "\n".join(lines)

    def _levels(self) -> str:
        def block(title: str, levels: list) -> str:
            if not levels:
                return f"{title}: none available"
            rows = "\n".join(f"  - {lv.label} = {lv.price} ({lv.basis})" for lv in levels)
            return f"{title}:\n{rows}"

        return (
            "## Candidate price levels\n"
            "Refer to these by label. Do not state a price of your own.\n"
            + block("Entries", self.levels.entries)
            + "\n"
            + block("Targets", self.levels.targets)
            + "\n"
            + block("Stops", self.levels.stops)
        )


def build_context(
    ticker: str,
    snapshot: IndicatorSnapshot,
    structure: PriceStructure | None,
    articles: list[NewsArticleOut],
    levels: CandidateLevels,
) -> AnalysisContext:
    return AnalysisContext(
        ticker=ticker,
        as_of=datetime.now(UTC),
        snapshot=snapshot,
        structure=structure,
        articles=articles,
        levels=levels,
    )


def _show(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _nums(*values: float | None) -> str:
    return " / ".join(_show(v) for v in values)


def _pcts(*values: float | None) -> str:
    return " / ".join("-" if v is None else f"{v * 100:.2f}%" for v in values)

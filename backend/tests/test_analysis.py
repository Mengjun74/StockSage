from datetime import UTC, datetime

import pytest

from app.analysis.agents import UnknownLevelError, build_verdict
from app.analysis.context import build_context
from app.analysis.levels import build_candidate_levels, risk_reward
from app.schemas.news import NewsArticleOut
from app.schemas.prices import IndicatorSnapshot, PriceStructure


def snapshot(**overrides) -> IndicatorSnapshot:
    return IndicatorSnapshot(**{"current_price": 100.0, "atr_14": 4.0, "rsi_14": 58.0, **overrides})


def structure(**overrides) -> PriceStructure:
    return PriceStructure(
        **{
            "trend": "bullish",
            "support_levels": [95.0, 90.0, 85.0],
            "resistance_levels": [108.0, 115.0, 124.0],
            "swing_highs": [108.0],
            "swing_lows": [95.0],
            "volume_state": "normal",
            "breakout_state": "range_bound",
            **overrides,
        }
    )


def test_targets_come_from_resistance_and_volatility() -> None:
    levels = build_candidate_levels(snapshot(), structure())

    assert levels is not None
    by_label = levels.by_label()
    assert by_label["resistance_1"].price == 108.0
    assert by_label["atr_target_2x"].price == 108.0  # 100 + 2 * 4
    assert by_label["atr_stop_1_5x"].price == 94.0
    assert by_label["support_1"].price == 95.0


def test_levels_on_the_wrong_side_of_price_are_excluded() -> None:
    """A "target" below the price or a "stop" above it is not a candidate."""
    levels = build_candidate_levels(
        snapshot(), structure(resistance_levels=[90.0, 108.0], support_levels=[95.0, 120.0])
    )

    assert levels is not None
    assert all(level.price > 100.0 for level in levels.targets)
    assert all(level.price < 100.0 for level in levels.stops)


def test_volatility_levels_exist_even_with_no_resistance_overhead() -> None:
    """At a high there is nothing above, and ATR still says how far a move tends to run."""
    levels = build_candidate_levels(snapshot(), structure(resistance_levels=[]))

    assert levels is not None
    assert [level.label for level in levels.targets] == ["atr_target_2x", "atr_target_3x"]


def test_no_atr_means_no_volatility_levels_rather_than_a_guess() -> None:
    levels = build_candidate_levels(snapshot(atr_14=None), structure())

    assert levels is not None
    assert all(not level.label.startswith("atr_") for level in levels.by_label().values())


def test_a_judge_inventing_a_price_is_rejected() -> None:
    """The point of labels is reproducible numbers; silently accepting an invented one
    would defeat that while appearing to work."""
    levels = build_candidate_levels(snapshot(), structure())
    assert levels is not None

    with pytest.raises(UnknownLevelError, match="target"):
        build_verdict(
            {"entry_label": "market", "target_label": "112.50", "stop_label": "support_1"}, levels
        )


def test_a_judge_choosing_listed_labels_is_accepted() -> None:
    levels = build_candidate_levels(snapshot(), structure())
    assert levels is not None

    verdict = build_verdict(
        {
            "action": "buy",
            "confidence": "medium",
            "horizon_days": 21,
            "entry_label": "market",
            "target_label": "resistance_2",
            "stop_label": "support_1",
            "reasoning": "r",
            "invalidation": "i",
            "disagreement": "d",
        },
        levels,
    )

    assert (verdict.entry.price, verdict.target.price, verdict.stop.price) == (100.0, 115.0, 95.0)
    assert verdict.risk_reward == 3.0  # (115-100) / (100-95)


def test_risk_reward_is_arithmetic_we_do_ourselves() -> None:
    assert risk_reward(100, 115, 95) == 3.0
    assert risk_reward(100, 110, 100) is None  # no risk defined
    assert risk_reward(100, 110, 105) is None  # stop above entry


def test_context_tells_the_agents_a_blank_52w_is_a_short_window() -> None:
    """Otherwise a missing value reads as "the market has no 52-week high"."""
    rendered = _context(articles=[]).render()

    assert "shorter than a year" in rendered


def test_context_says_quiet_news_is_not_a_signal() -> None:
    rendered = _context(articles=[]).render()

    assert "not itself a signal" in rendered


def test_context_carries_headlines_with_dates_for_citation() -> None:
    rendered = _context(
        articles=[
            NewsArticleOut(
                published_at=datetime(2026, 9, 20, tzinfo=UTC),
                source="yahoo_rss",
                publisher="Reuters",
                title="Chip export rules tightened",
                summary="Summary text",
                url="https://example.test/a",
            )
        ]
    ).render()

    assert "[2026-09-20] (Reuters) Chip export rules tightened" in rendered


def test_context_lists_every_candidate_label() -> None:
    rendered = _context(articles=[]).render()

    for label in ("market", "resistance_1", "atr_target_2x", "support_1", "atr_stop_1_5x"):
        assert label in rendered
    assert "Do not state a price of your own." in rendered


def _context(articles: list[NewsArticleOut]):
    levels = build_candidate_levels(snapshot(), structure())
    assert levels is not None
    return build_context("NVDA", snapshot(), structure(), articles, levels)


def test_analysis_is_unavailable_rather_than_broken_without_a_key() -> None:
    """Everything else keeps working when no model is configured."""
    from app.api.dependencies import AnalysisUnavailableError, get_analysis_pipeline
    from app.core.config import Settings, get_settings

    get_settings.cache_clear()
    try:
        import app.api.dependencies as deps

        original = deps.get_settings
        deps.get_settings = lambda: Settings(gemini_api_key=None)
        with pytest.raises(AnalysisUnavailableError, match="GEMINI_API_KEY"):
            get_analysis_pipeline()
    finally:
        deps.get_settings = original
        get_settings.cache_clear()


def test_filings_get_their_own_section_and_are_not_crowded_out() -> None:
    """Material filings are episodic and far fewer than headlines. Sharing one list
    and one cap would let a busy news day push the latest 10-Q out of view."""
    from app.analysis.context import MAX_ARTICLES

    headlines = [
        NewsArticleOut(
            published_at=datetime(2026, 9, 21, tzinfo=UTC),
            source="yahoo_rss",
            publisher="Reuters",
            title=f"Headline number {i}",
            summary=None,
            url=f"https://example.test/{i}",
        )
        for i in range(MAX_ARTICLES + 15)
    ]
    filing = NewsArticleOut(
        published_at=datetime(2026, 8, 26, tzinfo=UTC),
        source="sec_edgar",
        publisher="SEC EDGAR",
        title="NVDA filed 10-Q on 2026-08-26: Quarterly report filed with the SEC",
        summary="Items: 2.02 (results of operations)",
        url="https://example.test/filing",
    )

    rendered = _context(articles=[*headlines, filing]).render()

    assert "## SEC filings" in rendered
    assert "NVDA filed 10-Q on 2026-08-26" in rendered
    assert "Items: 2.02 (results of operations)" in rendered

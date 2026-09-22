"""Segmenting outcomes, which is how the tool is judged rather than described."""

from app.db.models.analysis import AnalysisOutcome
from app.pipelines.evaluation import _agrees, _hit_rate, _segment


def outcome(**overrides) -> AnalysisOutcome:
    return AnalysisOutcome(
        **{
            "ticker": "NVDA",
            "outcome": "target_hit",
            "entry_filled": True,
            "return_pct": 0.1,
            "max_adverse_pct": -0.03,
            "bars_evaluated": 10,
            "action": "buy",
            "confidence": "medium",
            "bull_strength": "strong",
            "bear_strength": "weak",
            "method_version": "t",
            **overrides,
        }
    )


def test_one_side_clearly_outweighing_the_other_counts_as_agreement() -> None:
    assert _agrees(outcome(bull_strength="strong", bear_strength="weak"))
    assert _agrees(outcome(bull_strength="weak", bear_strength="strong"))


def test_two_equally_strong_cases_are_a_balanced_call_not_an_agreement() -> None:
    """Both sides finding real evidence is genuine uncertainty. Counting it as
    agreement would hide exactly the distinction this table exists to test."""
    assert not _agrees(outcome(bull_strength="moderate", bear_strength="moderate"))
    assert not _agrees(outcome(bull_strength="strong", bear_strength="strong"))


def test_hit_rate_ignores_calls_the_market_never_resolved() -> None:
    """Expired and untriggered calls are neither wins nor losses; counting them as
    either would move the number without any trade having happened."""
    rows = [
        outcome(outcome="target_hit"),
        outcome(outcome="stop_hit"),
        outcome(outcome="expired"),
        outcome(outcome="not_triggered"),
    ]

    assert _hit_rate(rows) == 0.5


def test_hit_rate_is_absent_rather_than_zero_with_nothing_resolved() -> None:
    assert _hit_rate([outcome(outcome="expired")]) is None
    assert _hit_rate([]) is None


def test_a_segment_averages_only_the_values_it_has() -> None:
    segment = _segment("x", [outcome(return_pct=0.1), outcome(return_pct=None), outcome(return_pct=0.3)])

    assert segment.trades == 3
    assert segment.average_return_pct == 0.2

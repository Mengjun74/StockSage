"""The scoring rules, which decide whether this tool is worth trusting.

Every ambiguity here is resolved against the tool on purpose. A scorer that flatters
its own calls is worse than no scorer: it turns "I do not know if this works" into a
confident and wrong "it does".
"""

from datetime import UTC, datetime, timedelta

from app.analysis.evaluation import (
    EXPIRED,
    NOT_A_TRADE,
    NOT_TRIGGERED,
    STOP_HIT,
    TARGET_HIT,
    Call,
    evaluate,
)
from app.providers.base import PriceBar

START = datetime(2026, 9, 1, tzinfo=UTC)


def bars(spans: list[tuple[float, float]]) -> list[PriceBar]:
    """Each entry is one day's (low, high); open and close sit in the middle."""
    out = []
    for index, (low, high) in enumerate(spans):
        mid = (low + high) / 2
        out.append(
            PriceBar("NVDA", START + timedelta(days=index), mid, high, low, mid, mid, 1_000_000, "1d", "test")
        )
    return out


def call(**overrides) -> Call:
    return Call(
        **{
            "action": "buy",
            "entry_label": "market",
            "entry_price": 100.0,
            "target_price": 115.0,
            "stop_price": 95.0,
            "price_at_analysis": 100.0,
            **overrides,
        }
    )


def test_target_reached_is_a_win() -> None:
    result = evaluate(call(), bars([(99, 104), (103, 116)]))

    assert result.outcome == TARGET_HIT
    assert result.exit_price == 115.0
    assert result.return_pct == 0.15


def test_stop_reached_is_a_loss() -> None:
    result = evaluate(call(), bars([(99, 104), (94, 102)]))

    assert result.outcome == STOP_HIT
    assert result.return_pct == -0.05


def test_a_bar_spanning_both_counts_as_the_loss() -> None:
    """Daily bars cannot say which came first, so the ambiguity goes against the tool.
    Resolving it the other way would quietly inflate the hit rate."""
    result = evaluate(call(), bars([(94, 116)]))

    assert result.outcome == STOP_HIT


def test_neither_reached_by_the_horizon_expires_at_the_close() -> None:
    result = evaluate(call(), bars([(99, 104), (100, 106), (101, 108)]))

    assert result.outcome == EXPIRED
    assert result.exit_price == 104.5
    assert result.return_pct == 0.045


def test_a_pullback_entry_that_never_filled_is_neither_win_nor_loss() -> None:
    """Counting an untriggered call as a win because the stock rose would be scoring a
    trade that was never taken."""
    result = evaluate(
        call(entry_label="pullback_support_1", entry_price=90.0), bars([(99, 104), (103, 120)])
    )

    assert result.outcome == NOT_TRIGGERED
    assert result.entry_filled is False
    assert result.return_pct is None


def test_a_pullback_entry_is_scored_from_the_fill_not_the_call() -> None:
    result = evaluate(
        call(entry_label="pullback_support_1", entry_price=95.0, target_price=110.0, stop_price=90.0),
        bars([(99, 104), (94, 101), (100, 112)]),
    )

    assert result.outcome == TARGET_HIT
    assert result.entry_filled_at == START + timedelta(days=1)
    assert result.return_pct == round((110 - 95) / 95, 6)


def test_a_move_before_the_fill_does_not_count() -> None:
    """The target being tagged before entry filled is not a trade that was taken."""
    result = evaluate(
        call(entry_label="pullback_support_1", entry_price=95.0, target_price=110.0, stop_price=90.0),
        bars([(99, 112), (94, 101), (96, 99)]),
    )

    assert result.outcome == EXPIRED
    assert result.entry_filled_at == START + timedelta(days=1)


def test_avoid_is_not_scored_as_a_trade_but_is_still_judged() -> None:
    """An avoid before a fall was right; an avoid before a rally was not."""
    result = evaluate(call(action="avoid"), bars([(99, 104), (85, 100)]))

    assert result.outcome == NOT_A_TRADE
    assert result.entry_filled is False
    assert result.return_pct == round((92.5 - 100) / 100, 6)
    assert result.max_adverse_pct == -0.15


def test_excursions_record_how_close_the_call_came() -> None:
    """Max adverse excursion is how you learn a stop was too tight rather than the
    idea being wrong."""
    result = evaluate(call(), bars([(96, 104), (97, 114), (99, 116)]))

    assert result.outcome == TARGET_HIT
    assert result.max_adverse_pct == -0.04
    assert result.max_favorable_pct == 0.16


def test_no_bars_yet_is_not_an_outcome() -> None:
    result = evaluate(call(), [])

    assert result.outcome == NOT_TRIGGERED
    assert result.bars_evaluated == 0

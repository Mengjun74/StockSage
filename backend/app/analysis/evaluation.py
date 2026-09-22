"""Scoring a past call against what the market actually did.

No model is involved and nothing is fetched: the bars were stored when the call was
made. Whether the tool works is a question about prices, not about how convincing the
reasoning read.
"""

from dataclasses import dataclass
from datetime import datetime

from app.providers.base import PriceBar


METHOD_VERSION = "2026-09-22.1"

# Only these describe taking a long position. The others are still recorded, and
# still judged on what followed, but scoring them as trades would be dishonest.
TRADE_ACTIONS = {"buy", "accumulate_on_pullback"}

TARGET_HIT = "target_hit"
STOP_HIT = "stop_hit"
EXPIRED = "expired"
NOT_TRIGGERED = "not_triggered"
NOT_A_TRADE = "not_a_trade"


@dataclass(frozen=True)
class Outcome:
    outcome: str
    entry_filled: bool
    entry_filled_at: datetime | None
    exit_price: float | None
    exit_at: datetime | None
    return_pct: float | None
    max_favorable_pct: float | None
    max_adverse_pct: float | None
    bars_evaluated: int


@dataclass(frozen=True)
class Call:
    action: str
    entry_label: str
    entry_price: float
    target_price: float
    stop_price: float
    price_at_analysis: float


def evaluate(call: Call, bars: list[PriceBar]) -> Outcome:
    """Walk the bars that followed the call, in order.

    Where a single bar spans both the target and the stop, daily data cannot say which
    came first, and the stop is assumed. The point of this table is to find out whether
    the tool works, so every ambiguity is resolved against it.
    """
    if not bars:
        return Outcome(NOT_TRIGGERED, False, None, None, None, None, None, None, 0)

    if call.action not in TRADE_ACTIONS:
        # Not a trade, but what followed still matters: an "avoid" before a fall was
        # right, and an "avoid" before a rally was not.
        last = bars[-1]
        return Outcome(
            outcome=NOT_A_TRADE,
            entry_filled=False,
            entry_filled_at=None,
            exit_price=last.close,
            exit_at=last.timestamp,
            return_pct=_pct(call.price_at_analysis, last.close),
            max_favorable_pct=_pct(call.price_at_analysis, max(bar.high for bar in bars)),
            max_adverse_pct=_pct(call.price_at_analysis, min(bar.low for bar in bars)),
            bars_evaluated=len(bars),
        )

    fill_index = _fill_index(call, bars)
    if fill_index is None:
        return Outcome(NOT_TRIGGERED, False, None, None, None, None, None, None, len(bars))

    entry = call.entry_price
    filled_at = bars[fill_index].timestamp
    best = entry
    worst = entry

    for bar in bars[fill_index:]:
        best = max(best, bar.high)
        worst = min(worst, bar.low)
        if bar.low <= call.stop_price:
            return _closed(STOP_HIT, call, entry, call.stop_price, bar, filled_at, best, worst, len(bars))
        if bar.high >= call.target_price:
            return _closed(TARGET_HIT, call, entry, call.target_price, bar, filled_at, best, worst, len(bars))

    last = bars[-1]
    return _closed(EXPIRED, call, entry, last.close, last, filled_at, best, worst, len(bars))


def _fill_index(call: Call, bars: list[PriceBar]) -> int | None:
    """A market entry fills at once. A pullback entry only fills if the price comes
    back to it, and a call that never triggered is not a winner or a loser."""
    if call.entry_label == "market":
        return 0
    for index, bar in enumerate(bars):
        if bar.low <= call.entry_price <= bar.high:
            return index
    return None


def _closed(
    outcome: str,
    call: Call,
    entry: float,
    exit_price: float,
    bar: PriceBar,
    filled_at: datetime,
    best: float,
    worst: float,
    bars_evaluated: int,
) -> Outcome:
    return Outcome(
        outcome=outcome,
        entry_filled=True,
        entry_filled_at=filled_at,
        exit_price=round(exit_price, 4),
        exit_at=bar.timestamp,
        return_pct=_pct(entry, exit_price),
        max_favorable_pct=_pct(entry, best),
        max_adverse_pct=_pct(entry, worst),
        bars_evaluated=bars_evaluated,
    )


def _pct(start: float, end: float) -> float | None:
    if not start:
        return None
    return round((end - start) / start, 6)

"""Candidate prices, derived from the chart rather than proposed by a model.

The agents choose among these by label and never state a number of their own. A price
a model invents cannot be reproduced, cannot be checked, and cannot be scored later;
one derived here is all three.
"""

from dataclasses import dataclass

from app.schemas.prices import IndicatorSnapshot, PriceStructure


ATR_TARGET_MULTIPLES = (2.0, 3.0)
ATR_STOP_MULTIPLES = (1.5, 2.5)


@dataclass(frozen=True)
class PriceLevel:
    label: str
    price: float
    basis: str


@dataclass(frozen=True)
class CandidateLevels:
    current_price: float
    entries: list[PriceLevel]
    targets: list[PriceLevel]
    stops: list[PriceLevel]

    def by_label(self) -> dict[str, PriceLevel]:
        return {level.label: level for level in (*self.entries, *self.targets, *self.stops)}

    def resolve(self, label: str) -> PriceLevel | None:
        return self.by_label().get(label)


def build_candidate_levels(
    snapshot: IndicatorSnapshot | None, structure: PriceStructure | None
) -> CandidateLevels | None:
    if snapshot is None:
        return None

    current = snapshot.current_price
    atr = snapshot.atr_14
    resistances = sorted({r for r in (structure.resistance_levels if structure else []) if r > current})
    supports = sorted({s for s in (structure.support_levels if structure else []) if s < current}, reverse=True)

    entries = [PriceLevel("market", _round(current), "Current price")]
    for index, support in enumerate(supports[:2], start=1):
        entries.append(
            PriceLevel(
                f"pullback_support_{index}",
                _round(support),
                f"Wait for a pullback to support at {_round(support)}",
            )
        )

    targets = [
        PriceLevel(f"resistance_{index}", _round(level), f"Swing resistance at {_round(level)}")
        for index, level in enumerate(resistances[:3], start=1)
    ]
    stops = [
        PriceLevel(f"support_{index}", _round(level), f"Swing support at {_round(level)}")
        for index, level in enumerate(supports[:3], start=1)
    ]

    # ATR levels are always offered: near a high there may be no resistance overhead,
    # and volatility still says how far a move and a wrong call each tend to run.
    if atr:
        for multiple in ATR_TARGET_MULTIPLES:
            targets.append(
                PriceLevel(
                    f"atr_target_{_name(multiple)}",
                    _round(current + multiple * atr),
                    f"{multiple}x ATR({_round(atr)}) above the current price",
                )
            )
        for multiple in ATR_STOP_MULTIPLES:
            stops.append(
                PriceLevel(
                    f"atr_stop_{_name(multiple)}",
                    _round(current - multiple * atr),
                    f"{multiple}x ATR({_round(atr)}) below the current price",
                )
            )

    return CandidateLevels(
        current_price=_round(current),
        entries=entries,
        targets=sorted(targets, key=lambda level: level.price),
        stops=sorted(stops, key=lambda level: level.price, reverse=True),
    )


def risk_reward(entry: float, target: float, stop: float) -> float | None:
    """Computed here rather than asked of a model: it is arithmetic, and models are
    unreliable at arithmetic in a way that is hard to notice inside prose."""
    risk = entry - stop
    if risk <= 0:
        return None
    return _round((target - entry) / risk)


def _name(multiple: float) -> str:
    return f"{multiple:g}".replace(".", "_") + "x"


def _round(value: float) -> float:
    return round(float(value), 2)

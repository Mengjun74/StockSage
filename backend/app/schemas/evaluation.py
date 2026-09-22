from pydantic import BaseModel


class OutcomeCounts(BaseModel):
    target_hit: int = 0
    stop_hit: int = 0
    expired: int = 0
    not_triggered: int = 0
    not_a_trade: int = 0


class Segment(BaseModel):
    label: str
    trades: int
    hit_rate: float | None = None
    average_return_pct: float | None = None
    average_max_adverse_pct: float | None = None


class PerformanceReport(BaseModel):
    method_version: str
    analyses_scored: int
    trades_taken: int
    counts: OutcomeCounts
    hit_rate: float | None = None
    average_return_pct: float | None = None
    by_agreement: list[Segment] = []
    by_confidence: list[Segment] = []
    caveat: str = (
        "A handful of calls tells you nothing. Treat any of these numbers as noise "
        "until there are dozens, and remember they cover one market period."
    )

"""Rolling price statistics, computed from a plain list of
``(observed_at, effective_price)`` points — no I/O, no ORM, no DB session.
The caller (``pricing/history_service.py``) is responsible for fetching the
points; this module just does arithmetic, which is what makes it trivial to
unit test with hand-built fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median as _median
from statistics import pstdev


@dataclass(frozen=True)
class PricePoint:
    observed_at: datetime
    effective_price: Decimal


@dataclass(frozen=True)
class PriceStats:
    lowest: Decimal
    highest: Decimal
    average: Decimal
    median: Decimal
    avg_7d: Decimal | None
    avg_30d: Decimal | None
    avg_90d: Decimal | None
    previous_price: Decimal | None
    pct_change_vs_previous: Decimal | None
    observation_count: int
    history_span_days: int


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _window_average(points: list[PricePoint], now: datetime, days: int) -> Decimal | None:
    cutoff = now - timedelta(days=days)
    window = [p.effective_price for p in points if p.observed_at >= cutoff]
    if not window:
        return None
    return _round2(sum(window) / len(window))


def compute_price_stats(points: list[PricePoint], *, now: datetime) -> PriceStats:
    if not points:
        raise ValueError("compute_price_stats requires at least one price point")

    ordered = sorted(points, key=lambda p: p.observed_at)
    prices = [p.effective_price for p in ordered]

    previous_price = ordered[-2].effective_price if len(ordered) >= 2 else None
    current_price = ordered[-1].effective_price
    pct_change: Decimal | None = None
    if previous_price is not None and previous_price != 0:
        pct_change = _round2((current_price - previous_price) / previous_price * Decimal("100"))

    span_days = (ordered[-1].observed_at - ordered[0].observed_at).days

    return PriceStats(
        lowest=min(prices),
        highest=max(prices),
        average=_round2(sum(prices) / len(prices)),
        median=_round2(Decimal(str(_median(prices)))),
        avg_7d=_window_average(ordered, now, 7),
        avg_30d=_window_average(ordered, now, 30),
        avg_90d=_window_average(ordered, now, 90),
        previous_price=previous_price,
        pct_change_vs_previous=pct_change,
        observation_count=len(ordered),
        history_span_days=span_days,
    )


def pct_below(current: Decimal, reference: Decimal) -> Decimal | None:
    """How far below ``reference`` (e.g. 30-day avg, historical min)
    ``current`` sits, as a positive percentage. Negative means *above* the
    reference (a worse-than-usual price).
    """
    if reference == 0:
        return None
    return _round2((reference - current) / reference * Decimal("100"))


def price_consistency_ratio(points: list[PricePoint]) -> Decimal:
    """Population stddev of price / mean price. Lower = more consistent
    pricing history, which Deal Confidence rewards (a listing whose price
    swings wildly is harder to make a confident historical claim about).
    Returns 0 for a single observation (nothing to measure variance over).
    """
    prices = [float(p.effective_price) for p in points]
    if len(prices) < 2:
        return Decimal("0")
    mean_price = sum(prices) / len(prices)
    if mean_price == 0:
        return Decimal("0")
    return _round2(Decimal(str(pstdev(prices) / mean_price)))

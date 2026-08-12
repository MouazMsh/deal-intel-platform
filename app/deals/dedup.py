"""Decides whether a re-qualified deal is worth republishing.

A product is only republished when something meaningful happens: a
significant price decrease, a new coupon, stock returning, the score
improving significantly, or the configured cooldown expiring — never just
because a scheduled scan happened to run again with the same result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.enums import Availability

DEFAULT_SIGNIFICANT_PRICE_DROP_PCT = Decimal("5")
DEFAULT_SIGNIFICANT_SCORE_INCREASE = 10


@dataclass(frozen=True)
class DedupDecision:
    should_publish: bool
    reason: str


def evaluate_republish(
    *,
    previous_deal_score: int | None,
    previous_qualified_at: datetime | None,
    previous_had_coupon: bool,
    previous_availability: Availability | None,
    previous_price: Decimal | None,
    new_deal_score: int,
    new_price: Decimal,
    new_has_coupon: bool,
    new_availability: Availability,
    now: datetime,
    cooldown_hours: int,
    significant_price_drop_pct: Decimal = DEFAULT_SIGNIFICANT_PRICE_DROP_PCT,
    significant_score_increase: int = DEFAULT_SIGNIFICANT_SCORE_INCREASE,
) -> DedupDecision:
    if previous_qualified_at is None:
        return DedupDecision(True, "first_time_qualified")

    if previous_availability == Availability.OUT_OF_STOCK and new_availability != Availability.OUT_OF_STOCK:
        return DedupDecision(True, "back_in_stock")

    if previous_price is not None and previous_price > 0:
        price_drop_pct = (previous_price - new_price) / previous_price * Decimal("100")
        if price_drop_pct >= significant_price_drop_pct:
            return DedupDecision(True, "significant_price_decrease")

    if new_has_coupon and not previous_had_coupon:
        return DedupDecision(True, "new_coupon")

    if previous_deal_score is not None and (new_deal_score - previous_deal_score) >= significant_score_increase:
        return DedupDecision(True, "deal_score_increased")

    if now - previous_qualified_at >= timedelta(hours=cooldown_hours):
        return DedupDecision(True, "cooldown_expired")

    return DedupDecision(False, "no_meaningful_change_within_cooldown")

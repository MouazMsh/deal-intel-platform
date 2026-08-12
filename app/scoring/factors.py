"""Individual Deal Score / Deal Confidence factors.

Every factor returns a ``FactorResult`` — a 0..1 contribution plus
Arabic/English reasons — never just a bare number. This is what makes
``scoring/explanation.py`` able to generate "Why is this a deal?" directly
from the same values that produced the score, instead of maintaining a
second, potentially-inconsistent explanation system.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FactorResult:
    contribution: float  # 0.0 - 1.0
    reason_ar: str
    reason_en: str


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# --- Deal Score factors -----------------------------------------------------


def discount_vs_avg30_factor(effective_price: Decimal, avg_30d: Decimal | None) -> FactorResult:
    if avg_30d is None or avg_30d == 0:
        return FactorResult(0.0, "لا توجد بيانات كافية عن متوسط السعر", "Not enough 30-day price data")

    pct_below = float((avg_30d - effective_price) / avg_30d * 100)
    # Full credit at 30%+ below the 30-day average; scales linearly below that.
    contribution = _clamp(pct_below / 30.0)
    if pct_below <= 0:
        return FactorResult(
            0.0,
            f"السعر الحالي ليس أقل من متوسط 30 يوم (السعر أعلى بـ {abs(pct_below):.0f}%)",
            f"Current price is not below the 30-day average (+{abs(pct_below):.0f}%)",
        )
    return FactorResult(
        contribution,
        f"أقل من متوسط 30 يوم بـ {pct_below:.0f}%",
        f"{pct_below:.0f}% below the 30-day average",
    )


def discount_vs_min_factor(effective_price: Decimal, historical_min: Decimal) -> FactorResult:
    if historical_min == 0:
        return FactorResult(0.0, "لا توجد بيانات كافية عن أقل سعر مسجل", "Not enough historical minimum data")

    if effective_price <= historical_min:
        return FactorResult(1.0, "أقل سعر مسجل في التاريخ المتتبع", "Lowest price ever recorded")

    pct_above_min = float((effective_price - historical_min) / historical_min * 100)
    # Full credit if within 5% of the historical minimum; decays after that.
    contribution = _clamp(1.0 - (pct_above_min / 20.0))
    if contribution <= 0:
        return FactorResult(
            0.0,
            "السعر أعلى بشكل ملحوظ من أقل سعر مسجل",
            "Price is well above the historical minimum",
        )
    return FactorResult(
        contribution,
        f"قريب من أقل سعر مسجل (أعلى بـ {pct_above_min:.0f}%)",
        f"Close to the historical minimum (+{pct_above_min:.0f}%)",
    )


def seller_quality_factor(
    seller_rating: float | None, seller_review_count: int | None, blacklisted: bool
) -> FactorResult:
    if blacklisted:
        return FactorResult(0.0, "البائع محظور", "Seller is blacklisted")
    if seller_rating is None:
        return FactorResult(0.3, "تقييم البائع غير متوفر", "Seller rating unavailable")

    rating_component = _clamp(seller_rating / 5.0)
    # Review count matters, but with diminishing returns -- 500+ reviews is
    # already "plenty of evidence"; more than that doesn't add confidence.
    volume_component = _clamp((seller_review_count or 0) / 500.0)
    contribution = _clamp(0.7 * rating_component + 0.3 * volume_component)

    if seller_rating >= 4.5:
        return FactorResult(contribution, f"بائع بتقييم {seller_rating:.1f}/5", f"Seller rated {seller_rating:.1f}/5")
    return FactorResult(contribution, f"تقييم البائع {seller_rating:.1f}/5", f"Seller rating {seller_rating:.1f}/5")


def product_rating_factor(rating: float | None, review_count: int | None) -> FactorResult:
    if rating is None:
        return FactorResult(0.3, "تقييم المنتج غير متوفر", "Product rating unavailable")

    rating_component = _clamp(rating / 5.0)
    volume_component = _clamp((review_count or 0) / 1000.0)
    contribution = _clamp(0.7 * rating_component + 0.3 * volume_component)
    return FactorResult(
        contribution, f"تقييم المنتج {rating:.1f}/5 ({review_count or 0} تقييم)", f"Product rated {rating:.1f}/5"
    )


def coupon_factor(coupon_code: str | None, price: Decimal, effective_price: Decimal) -> FactorResult:
    if not coupon_code:
        return FactorResult(0.0, "", "")

    savings = price - effective_price
    if savings <= 0 or price == 0:
        return FactorResult(0.0, "", "")

    pct_savings = float(savings / price * 100)
    contribution = _clamp(pct_savings / 15.0)  # full credit at 15%+ coupon savings
    return FactorResult(
        contribution,
        f"كوبون إضافي يوفر {savings:.0f} ريال",
        f"Extra coupon saves {savings:.0f} SAR",
    )


# --- Deal Confidence factors -------------------------------------------------


def observation_count_factor(observation_count: int) -> FactorResult:
    contribution = _clamp(observation_count / 10.0)  # full credit at 10+ observations
    return FactorResult(
        contribution,
        f"{observation_count} رصد سعري مسجل",
        f"{observation_count} price observation(s) recorded",
    )


def history_age_factor(history_span_days: int) -> FactorResult:
    contribution = _clamp(history_span_days / 30.0)  # full credit at 30+ days of history
    return FactorResult(
        contribution,
        f"بيانات السعر تغطي {history_span_days} يوم",
        f"Price history spans {history_span_days} day(s)",
    )


def price_consistency_factor(stddev_ratio: Decimal) -> FactorResult:
    # A stddev/mean ratio of 0 is perfectly consistent; 0.2+ is quite volatile.
    contribution = _clamp(1.0 - (float(stddev_ratio) / 0.2))
    return FactorResult(contribution, "استقرار السعر التاريخي", "Historical price consistency")


def data_completeness_factor(present_optional_fields: int, total_optional_fields: int) -> FactorResult:
    if total_optional_fields == 0:
        return FactorResult(1.0, "بيانات كاملة", "Complete data")
    contribution = _clamp(present_optional_fields / total_optional_fields)
    return FactorResult(contribution, "اكتمال بيانات المنتج والبائع", "Product/seller data completeness")

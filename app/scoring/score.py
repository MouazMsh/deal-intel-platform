from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.scoring import factors
from app.scoring.config import SCORE_WEIGHTS


@dataclass(frozen=True)
class ScoreResult:
    score: int  # 0-100
    breakdown: dict[str, dict[str, object]]


def compute_deal_score(
    *,
    effective_price: Decimal,
    price: Decimal,
    avg_30d: Decimal | None,
    historical_min: Decimal,
    seller_rating: float | None,
    seller_review_count: int | None,
    seller_blacklisted: bool,
    product_rating: float | None,
    product_review_count: int | None,
    coupon_code: str | None,
) -> ScoreResult:
    factor_results: dict[str, factors.FactorResult] = {
        "discount_vs_avg30": factors.discount_vs_avg30_factor(effective_price, avg_30d),
        "discount_vs_min": factors.discount_vs_min_factor(effective_price, historical_min),
        "seller_quality": factors.seller_quality_factor(seller_rating, seller_review_count, seller_blacklisted),
        "product_rating": factors.product_rating_factor(product_rating, product_review_count),
        "coupon": factors.coupon_factor(coupon_code, price, effective_price),
    }

    breakdown: dict[str, dict[str, object]] = {}
    total = 0.0
    for name, result in factor_results.items():
        weight = SCORE_WEIGHTS[name]
        weighted_points = result.contribution * weight
        total += weighted_points
        breakdown[name] = {
            "contribution": round(result.contribution, 3),
            "weight": weight,
            "weighted_points": round(weighted_points, 2),
            "reason_ar": result.reason_ar,
            "reason_en": result.reason_en,
        }

    score = max(0, min(100, round(total)))
    return ScoreResult(score=score, breakdown=breakdown)

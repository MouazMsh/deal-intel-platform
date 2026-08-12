from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.scoring import factors
from app.scoring.config import CONFIDENCE_WEIGHTS


@dataclass(frozen=True)
class ConfidenceResult:
    confidence: int  # 0-100
    breakdown: dict[str, dict[str, object]]


def compute_deal_confidence(
    *,
    observation_count: int,
    history_span_days: int,
    price_consistency_ratio: Decimal,
    present_optional_fields: int,
    total_optional_fields: int,
) -> ConfidenceResult:
    factor_results: dict[str, factors.FactorResult] = {
        "observation_count": factors.observation_count_factor(observation_count),
        "history_age": factors.history_age_factor(history_span_days),
        "price_consistency": factors.price_consistency_factor(price_consistency_ratio),
        "data_completeness": factors.data_completeness_factor(present_optional_fields, total_optional_fields),
    }

    breakdown: dict[str, dict[str, object]] = {}
    total = 0.0
    for name, result in factor_results.items():
        weight = CONFIDENCE_WEIGHTS[name]
        weighted_points = result.contribution * weight
        total += weighted_points
        breakdown[name] = {
            "contribution": round(result.contribution, 3),
            "weight": weight,
            "weighted_points": round(weighted_points, 2),
            "reason_ar": result.reason_ar,
            "reason_en": result.reason_en,
        }

    confidence = max(0, min(100, round(total)))
    return ConfidenceResult(confidence=confidence, breakdown=breakdown)

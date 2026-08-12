"""Deal Score / Deal Confidence weight configuration.

Weights live here as one reviewable module rather than as individual env
vars — "configurable" is satisfied by there being exactly one place to
change them (and every factor function being independently unit-tested),
not by exploding the .env surface with a dozen tuning knobs nobody will
safely hand-tune blind. Both weight sets are validated to sum to 100 at
import time — a typo here fails immediately and loudly, not silently
mis-scores every deal.
"""

from __future__ import annotations

SCORE_WEIGHTS: dict[str, int] = {
    "discount_vs_avg30": 35,
    "discount_vs_min": 20,
    "seller_quality": 20,
    "product_rating": 15,
    "coupon": 10,
}

CONFIDENCE_WEIGHTS: dict[str, int] = {
    "observation_count": 30,
    "history_age": 30,
    "price_consistency": 25,
    "data_completeness": 15,
}

MIN_FUZZY_MATCH_CONFIDENCE = 85  # see app/matching/matcher.py

# Deal Grade thresholds — checked highest-first.
GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (95, "A+"),
    (90, "A"),
    (80, "B"),
    (70, "C"),
]  # anything below the lowest threshold is REJECT


def _validate_weights(name: str, weights: dict[str, int]) -> None:
    total = sum(weights.values())
    if total != 100:
        raise ValueError(f"{name} must sum to 100, got {total}: {weights!r}")


_validate_weights("SCORE_WEIGHTS", SCORE_WEIGHTS)
_validate_weights("CONFIDENCE_WEIGHTS", CONFIDENCE_WEIGHTS)

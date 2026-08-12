from __future__ import annotations

from decimal import Decimal

from app.domain.enums import DealClassification, DealGrade
from app.scoring.config import GRADE_THRESHOLDS

_DOWNGRADE_ORDER = [DealGrade.A_PLUS, DealGrade.A, DealGrade.B, DealGrade.C, DealGrade.REJECT]


def _letter_for_score(score: int) -> DealGrade:
    for threshold, grade_value in GRADE_THRESHOLDS:
        if score >= threshold:
            return DealGrade(grade_value)
    return DealGrade.REJECT


def _downgrade_one_level(grade: DealGrade) -> DealGrade:
    index = _DOWNGRADE_ORDER.index(grade)
    return _DOWNGRADE_ORDER[min(index + 1, len(_DOWNGRADE_ORDER) - 1)]


def grade_for(score: int, confidence: int, *, min_confidence_for_grade: int) -> DealGrade:
    """Deal Grade: the letter implied by the score, downgraded one level if
    confidence is below the configured floor. This is what makes
    ``Score: 94, Confidence: 35`` render differently from
    ``Score: 94, Confidence: 94`` (see ARCHITECTURE.md §4-8) — a low-
    confidence A+ shows up as A, not as an unqualified A+ claim.
    """
    grade = _letter_for_score(score)
    if confidence < min_confidence_for_grade:
        grade = _downgrade_one_level(grade)
    return grade


def classification_for(
    score: int,
    discount_pct_vs_avg30: Decimal | None,
    *,
    min_deal_score: int,
    flash_deal_threshold: int,
) -> DealClassification:
    if score < min_deal_score:
        return DealClassification.REJECT

    if discount_pct_vs_avg30 is not None and discount_pct_vs_avg30 >= flash_deal_threshold:
        return DealClassification.FLASH_DEAL

    if score >= 90:
        return DealClassification.INSANE_DEAL
    if score >= 80:
        return DealClassification.GREAT_DEAL
    if score >= min_deal_score:
        return DealClassification.GOOD_DEAL
    return DealClassification.NORMAL

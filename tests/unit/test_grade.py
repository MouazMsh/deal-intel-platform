from __future__ import annotations

from decimal import Decimal

from app.domain.enums import DealClassification, DealGrade
from app.scoring.grade import classification_for, grade_for


def test_high_score_high_confidence_gets_full_grade() -> None:
    assert grade_for(97, 95, min_confidence_for_grade=50) == DealGrade.A_PLUS


def test_high_score_low_confidence_is_downgraded_one_level() -> None:
    # Directly reproduces the approved spec's example: Score 94 (=A) with
    # low confidence should NOT render as an unqualified A.
    assert grade_for(94, 35, min_confidence_for_grade=50) == DealGrade.B


def test_high_score_high_confidence_is_not_downgraded() -> None:
    assert grade_for(94, 94, min_confidence_for_grade=50) == DealGrade.A


def test_reject_score_stays_reject_even_with_high_confidence() -> None:
    assert grade_for(50, 100, min_confidence_for_grade=50) == DealGrade.REJECT


def test_grade_thresholds() -> None:
    assert grade_for(95, 100, min_confidence_for_grade=0) == DealGrade.A_PLUS
    assert grade_for(90, 100, min_confidence_for_grade=0) == DealGrade.A
    assert grade_for(80, 100, min_confidence_for_grade=0) == DealGrade.B
    assert grade_for(70, 100, min_confidence_for_grade=0) == DealGrade.C
    assert grade_for(69, 100, min_confidence_for_grade=0) == DealGrade.REJECT


def test_reject_grade_downgrade_stays_reject() -> None:
    # REJECT is the floor of the downgrade order -- confirms it doesn't
    # wrap around or raise.
    assert grade_for(50, 0, min_confidence_for_grade=50) == DealGrade.REJECT


def test_classification_below_min_score_is_reject() -> None:
    result = classification_for(65, Decimal("10"), min_deal_score=70, flash_deal_threshold=20)
    assert result == DealClassification.REJECT


def test_classification_flash_deal_takes_priority() -> None:
    result = classification_for(75, Decimal("25"), min_deal_score=70, flash_deal_threshold=20)
    assert result == DealClassification.FLASH_DEAL


def test_classification_insane_deal() -> None:
    result = classification_for(92, Decimal("5"), min_deal_score=70, flash_deal_threshold=20)
    assert result == DealClassification.INSANE_DEAL


def test_classification_great_deal() -> None:
    result = classification_for(85, Decimal("5"), min_deal_score=70, flash_deal_threshold=20)
    assert result == DealClassification.GREAT_DEAL


def test_classification_good_deal() -> None:
    result = classification_for(72, Decimal("5"), min_deal_score=70, flash_deal_threshold=20)
    assert result == DealClassification.GOOD_DEAL

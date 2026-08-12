from __future__ import annotations

from app.scoring.explanation import build_explanation


def _breakdown(**entries: dict[str, object]) -> dict[str, dict[str, object]]:
    return entries


def test_material_factors_included_in_descending_order() -> None:
    breakdown = _breakdown(
        discount_vs_avg30={
            "weighted_points": 30.0,
            "reason_ar": "أقل من متوسط 30 يوم بـ 30%",
            "reason_en": "30% below the 30-day average",
        },
        seller_quality={
            "weighted_points": 5.0,
            "reason_ar": "بائع موثوق",
            "reason_en": "Trusted seller",
        },
    )
    explanation = build_explanation(breakdown, lang="en")
    assert explanation == ["30% below the 30-day average", "Trusted seller"]


def test_immaterial_factors_excluded() -> None:
    breakdown = _breakdown(
        tiny_factor={"weighted_points": 0.5, "reason_ar": "شيء صغير", "reason_en": "Tiny thing"},
    )
    explanation = build_explanation(breakdown, lang="en")
    assert explanation == []


def test_empty_reason_excluded_even_if_material() -> None:
    breakdown = _breakdown(
        coupon={"weighted_points": 10.0, "reason_ar": "", "reason_en": ""},
    )
    explanation = build_explanation(breakdown, lang="en")
    assert explanation == []


def test_arabic_language_selection() -> None:
    breakdown = _breakdown(
        discount_vs_avg30={
            "weighted_points": 20.0,
            "reason_ar": "أقل من متوسط 30 يوم",
            "reason_en": "Below the 30-day average",
        },
    )
    explanation = build_explanation(breakdown, lang="ar")
    assert explanation == ["أقل من متوسط 30 يوم"]

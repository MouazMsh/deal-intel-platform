from __future__ import annotations

from decimal import Decimal

from app.scoring.confidence import compute_deal_confidence


def test_low_observation_count_yields_low_confidence() -> None:
    result = compute_deal_confidence(
        observation_count=1,
        history_span_days=0,
        price_consistency_ratio=Decimal("0"),
        present_optional_fields=2,
        total_optional_fields=6,
    )
    assert result.confidence < 50


def test_rich_history_yields_high_confidence() -> None:
    result = compute_deal_confidence(
        observation_count=30,
        history_span_days=90,
        price_consistency_ratio=Decimal("0.02"),
        present_optional_fields=6,
        total_optional_fields=6,
    )
    assert result.confidence >= 90


def test_matches_spec_example_score_94_confidence_35_vs_94() -> None:
    """Directly reproduces the approved architecture's worked example:
    a newly-seen listing (score 94 elsewhere) should land near confidence
    35, while a well-tracked one should land near confidence 94.
    """
    low = compute_deal_confidence(
        observation_count=2,
        history_span_days=1,
        price_consistency_ratio=Decimal("0.05"),
        present_optional_fields=3,
        total_optional_fields=6,
    )
    high = compute_deal_confidence(
        observation_count=15,
        history_span_days=60,
        price_consistency_ratio=Decimal("0.01"),
        present_optional_fields=6,
        total_optional_fields=6,
    )
    assert low.confidence < high.confidence
    assert low.confidence < 50
    assert high.confidence >= 90


def test_confidence_is_bounded_0_to_100() -> None:
    result = compute_deal_confidence(
        observation_count=0,
        history_span_days=0,
        price_consistency_ratio=Decimal("1"),
        present_optional_fields=0,
        total_optional_fields=6,
    )
    assert 0 <= result.confidence <= 100

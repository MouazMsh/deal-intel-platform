from __future__ import annotations

from decimal import Decimal

from app.scoring.score import compute_deal_score


def _score(**overrides: object) -> int:
    defaults: dict[str, object] = dict(
        effective_price=Decimal("899.00"),
        price=Decimal("899.00"),
        avg_30d=Decimal("1399.00"),
        historical_min=Decimal("899.00"),
        seller_rating=4.6,
        seller_review_count=120000,
        seller_blacklisted=False,
        product_rating=4.7,
        product_review_count=3200,
        coupon_code=None,
    )
    defaults.update(overrides)
    return compute_deal_score(**defaults).score  # type: ignore[arg-type]


def test_strong_deal_scores_high() -> None:
    score = _score()
    assert score >= 80


def test_no_discount_no_history_scores_low() -> None:
    score = _score(
        effective_price=Decimal("100.00"),
        price=Decimal("100.00"),
        avg_30d=None,
        historical_min=Decimal("100.00"),
        seller_rating=None,
        seller_review_count=None,
        product_rating=None,
        product_review_count=None,
    )
    assert score < 50


def test_blacklisted_seller_reduces_score() -> None:
    normal = _score(seller_blacklisted=False)
    blacklisted = _score(seller_blacklisted=True)
    assert blacklisted < normal


def test_score_is_bounded_0_to_100() -> None:
    assert 0 <= _score() <= 100
    assert 0 <= _score(effective_price=Decimal("0.01"), historical_min=Decimal("0.01")) <= 100


def test_breakdown_contains_all_configured_factors() -> None:
    result = compute_deal_score(
        effective_price=Decimal("899.00"),
        price=Decimal("899.00"),
        avg_30d=Decimal("1399.00"),
        historical_min=Decimal("899.00"),
        seller_rating=4.6,
        seller_review_count=120000,
        seller_blacklisted=False,
        product_rating=4.7,
        product_review_count=3200,
        coupon_code=None,
    )
    assert set(result.breakdown.keys()) == {
        "discount_vs_avg30",
        "discount_vs_min",
        "seller_quality",
        "product_rating",
        "coupon",
    }

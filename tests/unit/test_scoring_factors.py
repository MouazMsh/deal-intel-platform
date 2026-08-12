from __future__ import annotations

from decimal import Decimal

from app.scoring import factors


def test_discount_vs_avg30_no_discount_is_zero() -> None:
    result = factors.discount_vs_avg30_factor(Decimal("100.00"), Decimal("100.00"))
    assert result.contribution == 0.0


def test_discount_vs_avg30_above_average_is_zero() -> None:
    result = factors.discount_vs_avg30_factor(Decimal("110.00"), Decimal("100.00"))
    assert result.contribution == 0.0


def test_discount_vs_avg30_thirty_percent_below_is_full_credit() -> None:
    result = factors.discount_vs_avg30_factor(Decimal("70.00"), Decimal("100.00"))
    assert result.contribution == 1.0


def test_discount_vs_avg30_no_data_returns_zero_with_reason() -> None:
    result = factors.discount_vs_avg30_factor(Decimal("100.00"), None)
    assert result.contribution == 0.0
    assert result.reason_en


def test_discount_vs_min_at_minimum_is_full_credit() -> None:
    result = factors.discount_vs_min_factor(Decimal("50.00"), Decimal("50.00"))
    assert result.contribution == 1.0
    assert "Lowest" in result.reason_en


def test_discount_vs_min_below_minimum_is_full_credit() -> None:
    result = factors.discount_vs_min_factor(Decimal("40.00"), Decimal("50.00"))
    assert result.contribution == 1.0


def test_discount_vs_min_far_above_is_zero() -> None:
    result = factors.discount_vs_min_factor(Decimal("100.00"), Decimal("50.00"))
    assert result.contribution == 0.0


def test_seller_quality_blacklisted_is_zero() -> None:
    result = factors.seller_quality_factor(4.9, 10000, blacklisted=True)
    assert result.contribution == 0.0


def test_seller_quality_high_rating_high_volume() -> None:
    result = factors.seller_quality_factor(4.8, 100000, blacklisted=False)
    assert result.contribution > 0.9


def test_seller_quality_missing_rating() -> None:
    result = factors.seller_quality_factor(None, None, blacklisted=False)
    assert result.contribution == 0.3


def test_product_rating_factor_missing() -> None:
    result = factors.product_rating_factor(None, None)
    assert result.contribution == 0.3


def test_coupon_factor_no_coupon_is_zero() -> None:
    result = factors.coupon_factor(None, Decimal("100.00"), Decimal("100.00"))
    assert result.contribution == 0.0


def test_coupon_factor_with_savings() -> None:
    result = factors.coupon_factor("SAVE50", Decimal("400.00"), Decimal("350.00"))
    assert result.contribution > 0.0
    assert "50" in result.reason_en


def test_observation_count_factor_scales() -> None:
    low = factors.observation_count_factor(1)
    high = factors.observation_count_factor(10)
    assert low.contribution < high.contribution
    assert high.contribution == 1.0


def test_history_age_factor_scales() -> None:
    low = factors.history_age_factor(1)
    high = factors.history_age_factor(30)
    assert low.contribution < high.contribution
    assert high.contribution == 1.0


def test_price_consistency_factor_zero_ratio_is_full_credit() -> None:
    result = factors.price_consistency_factor(Decimal("0"))
    assert result.contribution == 1.0


def test_price_consistency_factor_volatile_is_low() -> None:
    result = factors.price_consistency_factor(Decimal("0.5"))
    assert result.contribution == 0.0


def test_data_completeness_factor() -> None:
    result = factors.data_completeness_factor(3, 6)
    assert result.contribution == 0.5

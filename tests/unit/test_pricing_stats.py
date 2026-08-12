from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.pricing.stats import PricePoint, compute_price_stats, pct_below, price_consistency_ratio

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _points(*prices_days_ago: tuple[str, int]) -> list[PricePoint]:
    return [
        PricePoint(observed_at=_NOW - timedelta(days=days), effective_price=Decimal(price))
        for price, days in prices_days_ago
    ]


def test_single_observation_stats() -> None:
    points = _points(("100.00", 0))
    stats = compute_price_stats(points, now=_NOW)
    assert stats.lowest == Decimal("100.00")
    assert stats.highest == Decimal("100.00")
    assert stats.average == Decimal("100.00")
    assert stats.previous_price is None
    assert stats.pct_change_vs_previous is None
    assert stats.observation_count == 1
    assert stats.history_span_days == 0


def test_multi_observation_rolling_averages() -> None:
    points = _points(("100.00", 40), ("90.00", 10), ("80.00", 3), ("70.00", 0))
    stats = compute_price_stats(points, now=_NOW)
    assert stats.lowest == Decimal("70.00")
    assert stats.highest == Decimal("100.00")
    assert stats.observation_count == 4
    # avg_7d should only include the 3-day-ago and 0-day-ago points.
    assert stats.avg_7d == Decimal("75.00")
    # avg_30d should include 10, 3, 0 day-ago points (90+80+70)/3 = 80.
    assert stats.avg_30d == Decimal("80.00")
    # avg_90d includes all 4 points.
    assert stats.avg_90d == Decimal("85.00")
    assert stats.previous_price == Decimal("80.00")
    assert stats.pct_change_vs_previous == Decimal("-12.50")


def test_compute_price_stats_requires_at_least_one_point() -> None:
    with pytest.raises(ValueError):
        compute_price_stats([], now=_NOW)


def test_pct_below() -> None:
    assert pct_below(Decimal("80.00"), Decimal("100.00")) == Decimal("20.00")
    assert pct_below(Decimal("120.00"), Decimal("100.00")) == Decimal("-20.00")


def test_pct_below_zero_reference_returns_none() -> None:
    assert pct_below(Decimal("50.00"), Decimal("0")) is None


def test_price_consistency_ratio_single_point_is_zero() -> None:
    assert price_consistency_ratio(_points(("100.00", 0))) == Decimal("0")


def test_price_consistency_ratio_identical_prices_is_zero() -> None:
    points = _points(("100.00", 10), ("100.00", 5), ("100.00", 0))
    assert price_consistency_ratio(points) == Decimal("0")


def test_price_consistency_ratio_varying_prices_is_positive() -> None:
    points = _points(("50.00", 10), ("150.00", 5), ("100.00", 0))
    assert price_consistency_ratio(points) > Decimal("0")

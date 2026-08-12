from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.deals.freshness import classify_freshness
from app.domain.enums import Freshness

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def test_just_verified_is_fresh() -> None:
    assert classify_freshness(_NOW, _NOW) == Freshness.FRESH


def test_ten_minutes_ago_is_fresh() -> None:
    assert classify_freshness(_NOW - timedelta(minutes=10), _NOW) == Freshness.FRESH


def test_thirty_minutes_ago_is_recent() -> None:
    assert classify_freshness(_NOW - timedelta(minutes=30), _NOW) == Freshness.RECENT


def test_two_hours_ago_is_stale() -> None:
    assert classify_freshness(_NOW - timedelta(hours=2), _NOW) == Freshness.STALE


def test_custom_thresholds() -> None:
    result = classify_freshness(_NOW - timedelta(minutes=5), _NOW, fresh_minutes=1, recent_minutes=10)
    assert result == Freshness.RECENT

from __future__ import annotations

from datetime import datetime

from app.domain.enums import Freshness


def classify_freshness(
    last_verified_at: datetime,
    now: datetime,
    *,
    fresh_minutes: int = 15,
    recent_minutes: int = 60,
) -> Freshness:
    age_minutes = (now - last_verified_at).total_seconds() / 60
    if age_minutes < fresh_minutes:
        return Freshness.FRESH
    if age_minutes < recent_minutes:
        return Freshness.RECENT
    return Freshness.STALE

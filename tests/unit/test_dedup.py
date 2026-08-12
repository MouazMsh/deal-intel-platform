from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.deals.dedup import evaluate_republish
from app.domain.enums import Availability

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _base_kwargs(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = dict(
        previous_deal_score=80,
        previous_qualified_at=_NOW - timedelta(hours=1),
        previous_had_coupon=False,
        previous_availability=Availability.IN_STOCK,
        previous_price=Decimal("899.00"),
        new_deal_score=80,
        new_price=Decimal("899.00"),
        new_has_coupon=False,
        new_availability=Availability.IN_STOCK,
        now=_NOW,
        cooldown_hours=24,
    )
    defaults.update(overrides)
    return defaults


def test_first_time_qualified_always_publishes() -> None:
    decision = evaluate_republish(**_base_kwargs(previous_qualified_at=None))
    assert decision.should_publish is True
    assert decision.reason == "first_time_qualified"


def test_no_meaningful_change_within_cooldown_does_not_republish() -> None:
    decision = evaluate_republish(**_base_kwargs())
    assert decision.should_publish is False
    assert decision.reason == "no_meaningful_change_within_cooldown"


def test_back_in_stock_triggers_republish() -> None:
    decision = evaluate_republish(
        **_base_kwargs(previous_availability=Availability.OUT_OF_STOCK, new_availability=Availability.IN_STOCK)
    )
    assert decision.should_publish is True
    assert decision.reason == "back_in_stock"


def test_significant_price_drop_triggers_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(new_price=Decimal("800.00")))  # ~11% drop
    assert decision.should_publish is True
    assert decision.reason == "significant_price_decrease"


def test_small_price_drop_does_not_trigger_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(new_price=Decimal("895.00")))  # <1% drop
    assert decision.should_publish is False


def test_new_coupon_triggers_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(previous_had_coupon=False, new_has_coupon=True))
    assert decision.should_publish is True
    assert decision.reason == "new_coupon"


def test_significant_score_increase_triggers_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(previous_deal_score=70, new_deal_score=85))
    assert decision.should_publish is True
    assert decision.reason == "deal_score_increased"


def test_cooldown_expiry_triggers_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(previous_qualified_at=_NOW - timedelta(hours=25)))
    assert decision.should_publish is True
    assert decision.reason == "cooldown_expired"


def test_cooldown_not_yet_expired_does_not_republish() -> None:
    decision = evaluate_republish(**_base_kwargs(previous_qualified_at=_NOW - timedelta(hours=23)))
    assert decision.should_publish is False

from __future__ import annotations

from app.domain.enums import (
    Availability,
    DealClassification,
    DealGrade,
    DiscountType,
    Environment,
    Freshness,
    LifecycleStatus,
    MarketplaceCode,
    PublishedDealStatus,
)


def test_environment_values() -> None:
    assert {e.value for e in Environment} == {"development", "test", "production"}


def test_marketplace_code_values() -> None:
    assert {m.value for m in MarketplaceCode} == {"amazon_sa", "noon_sa"}


def test_deal_grade_ordering_values_match_spec() -> None:
    assert DealGrade.A_PLUS.value == "A+"
    assert DealGrade.A.value == "A"
    assert DealGrade.B.value == "B"
    assert DealGrade.C.value == "C"
    assert DealGrade.REJECT.value == "REJECT"


def test_deal_classification_includes_flash_deal() -> None:
    assert DealClassification.FLASH_DEAL.value == "FLASH_DEAL"


def test_lifecycle_status_covers_full_state_machine_vocabulary() -> None:
    expected = {
        "discovered",
        "qualified",
        "published",
        "price_changed",
        "expired",
        "rejected",
        "out_of_stock",
        "blacklisted",
    }
    assert {s.value for s in LifecycleStatus} == expected


def test_freshness_values() -> None:
    assert {f.value for f in Freshness} == {"fresh", "recent", "stale"}


def test_availability_values() -> None:
    assert {a.value for a in Availability} == {"in_stock", "out_of_stock", "limited", "unknown"}


def test_discount_type_values() -> None:
    assert {d.value for d in DiscountType} == {"fixed", "percentage"}


def test_published_deal_status_values() -> None:
    assert {s.value for s in PublishedDealStatus} == {"active", "price_changed", "expired"}

from __future__ import annotations

import pytest

from app.deals.lifecycle import InvalidLifecycleTransitionError, transition
from app.domain.enums import LifecycleStatus


def test_same_state_transition_is_idempotent_noop() -> None:
    assert transition(LifecycleStatus.QUALIFIED, LifecycleStatus.QUALIFIED) == LifecycleStatus.QUALIFIED


def test_discovered_to_qualified_is_allowed() -> None:
    assert transition(LifecycleStatus.DISCOVERED, LifecycleStatus.QUALIFIED) == LifecycleStatus.QUALIFIED


def test_qualified_to_published_is_allowed() -> None:
    assert transition(LifecycleStatus.QUALIFIED, LifecycleStatus.PUBLISHED) == LifecycleStatus.PUBLISHED


def test_published_to_price_changed_is_allowed() -> None:
    assert transition(LifecycleStatus.PUBLISHED, LifecycleStatus.PRICE_CHANGED) == LifecycleStatus.PRICE_CHANGED


def test_published_to_expired_is_allowed() -> None:
    assert transition(LifecycleStatus.PUBLISHED, LifecycleStatus.EXPIRED) == LifecycleStatus.EXPIRED


def test_rejected_can_requalify() -> None:
    assert transition(LifecycleStatus.REJECTED, LifecycleStatus.QUALIFIED) == LifecycleStatus.QUALIFIED


def test_out_of_stock_can_return_to_qualified() -> None:
    assert transition(LifecycleStatus.OUT_OF_STOCK, LifecycleStatus.QUALIFIED) == LifecycleStatus.QUALIFIED


def test_discovered_directly_to_published_is_invalid() -> None:
    with pytest.raises(InvalidLifecycleTransitionError):
        transition(LifecycleStatus.DISCOVERED, LifecycleStatus.PUBLISHED)


def test_blacklisted_is_terminal() -> None:
    with pytest.raises(InvalidLifecycleTransitionError):
        transition(LifecycleStatus.BLACKLISTED, LifecycleStatus.QUALIFIED)


def test_any_non_terminal_state_can_be_blacklisted() -> None:
    for state in (
        LifecycleStatus.DISCOVERED,
        LifecycleStatus.QUALIFIED,
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.PRICE_CHANGED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.REJECTED,
    ):
        assert transition(state, LifecycleStatus.BLACKLISTED) == LifecycleStatus.BLACKLISTED

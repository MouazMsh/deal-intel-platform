"""The Deal lifecycle state machine.

Idempotency comes from two rules, both enforced here rather than left to
caller discipline:

1. Transitioning to the state a Deal is *already* in is a no-op, not an
   error — re-running the same scan twice against unchanged data leaves
   ``lifecycle_status`` exactly where it was.
2. Every other transition must appear in ``ALLOWED_TRANSITIONS`` or
   ``transition()`` raises ``InvalidLifecycleTransitionError`` — an invalid
   transition fails loudly instead of silently corrupting state.
"""

from __future__ import annotations

from app.core.exceptions import AppError
from app.domain.enums import LifecycleStatus

ALLOWED_TRANSITIONS: dict[LifecycleStatus, set[LifecycleStatus]] = {
    LifecycleStatus.DISCOVERED: {
        LifecycleStatus.QUALIFIED,
        LifecycleStatus.REJECTED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.QUALIFIED: {
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.REJECTED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.PUBLISHED: {
        LifecycleStatus.PRICE_CHANGED,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.PRICE_CHANGED: {
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.OUT_OF_STOCK: {
        LifecycleStatus.QUALIFIED,
        LifecycleStatus.REJECTED,
        LifecycleStatus.DISCOVERED,
        LifecycleStatus.EXPIRED,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.EXPIRED: {LifecycleStatus.BLACKLISTED},
    LifecycleStatus.REJECTED: {
        LifecycleStatus.QUALIFIED,
        LifecycleStatus.OUT_OF_STOCK,
        LifecycleStatus.DISCOVERED,
        LifecycleStatus.BLACKLISTED,
    },
    LifecycleStatus.BLACKLISTED: set(),  # terminal; only an explicit admin action (Phase 6) can move it
}


class InvalidLifecycleTransitionError(AppError):
    pass


def transition(current: LifecycleStatus, target: LifecycleStatus) -> LifecycleStatus:
    if current == target:
        return current  # idempotent no-op

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidLifecycleTransitionError(
            f"Cannot transition Deal lifecycle from {current.value!r} to {target.value!r}."
        )
    return target

"""Shared domain enums.

These are the vocabulary the rest of the system is built on. They are defined
once here so the database models, provider DTOs, and (in later phases) the
scoring/lifecycle engine all reference the same values instead of scattering
magic strings.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Which environment the app is running in.

    This is not just informational — ``core.config.Settings`` uses it to
    decide which database, which Telegram channel, and which providers are
    allowed to be used. See the guardrails in ``providers/registry.py`` and
    ``telegram/publisher.py``.
    """

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class MarketplaceCode(str, Enum):
    """The set of marketplaces the platform knows about.

    Adding a future marketplace (Jarir, Extra, ...) means adding a value
    here plus a provider implementation — it must never require changes to
    the deal engine, pricing, or Telegram modules.
    """

    AMAZON_SA = "amazon_sa"
    NOON_SA = "noon_sa"


class Availability(str, Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED = "limited"
    UNKNOWN = "unknown"


class DiscountType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"


class DealGrade(str, Enum):
    """Human-facing grade. Derived from Deal Score and gated by Deal
    Confidence in Phase 2 — the enum lives here in Phase 1 because the
    ``Deal`` table needs a column for it now.
    """

    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    REJECT = "REJECT"


class DealClassification(str, Enum):
    INSANE_DEAL = "INSANE_DEAL"
    GREAT_DEAL = "GREAT_DEAL"
    GOOD_DEAL = "GOOD_DEAL"
    NORMAL = "NORMAL"
    FLASH_DEAL = "FLASH_DEAL"
    REJECT = "REJECT"


class LifecycleStatus(str, Enum):
    """The Deal lifecycle state machine. Valid transitions are enforced in
    Phase 2's ``deals/lifecycle.py`` — this enum only defines the vocabulary.
    """

    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    PUBLISHED = "published"
    PRICE_CHANGED = "price_changed"
    EXPIRED = "expired"
    REJECTED = "rejected"
    OUT_OF_STOCK = "out_of_stock"
    BLACKLISTED = "blacklisted"


class Freshness(str, Enum):
    FRESH = "fresh"
    RECENT = "recent"
    STALE = "stale"


class PublishedDealStatus(str, Enum):
    ACTIVE = "active"
    PRICE_CHANGED = "price_changed"
    EXPIRED = "expired"

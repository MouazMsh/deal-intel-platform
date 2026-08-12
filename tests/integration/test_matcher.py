from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CanonicalProduct
from app.domain.dto import RawProductObservation
from app.domain.enums import MarketplaceCode
from app.matching.matcher import resolve_canonical_product

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _observation(**overrides: object) -> RawProductObservation:
    defaults: dict[str, object] = dict(
        marketplace_code=MarketplaceCode.AMAZON_SA,
        marketplace_product_id="TEST-001",
        title="Sony WH-1000XM5 Wireless Headphones",
        brand="Sony",
        model="WH-1000XM5",
        product_url="https://www.amazon.sa/dp/TEST-001",
        price=Decimal("899.00"),
        observed_at=_NOW,
    )
    defaults.update(overrides)
    return RawProductObservation(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_gtin_exact_match(db_session: AsyncSession) -> None:
    existing = CanonicalProduct(canonical_title="Existing Product", gtin="1234567890123")
    db_session.add(existing)
    await db_session.flush()

    observation = _observation(gtin="1234567890123", title="A Totally Different Title")
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "gtin_exact"
    assert result.confidence == 100
    assert result.is_new is False
    assert result.canonical_product.id == existing.id


@pytest.mark.asyncio
async def test_brand_model_exact_match(db_session: AsyncSession) -> None:
    existing = CanonicalProduct(canonical_title="Sony WH-1000XM5", brand="Sony", model="WH-1000XM5")
    db_session.add(existing)
    await db_session.flush()

    observation = _observation(brand="sony", model="wh-1000xm5")  # different casing
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "brand_model_exact"
    assert result.confidence == 95
    assert result.canonical_product.id == existing.id


@pytest.mark.asyncio
async def test_fuzzy_title_match_within_same_brand(db_session: AsyncSession) -> None:
    """Word-order/punctuation variance is exactly what fuzzy (token-sort)
    matching is for -- both titles share the identical word set, just
    reordered, so this is a deterministic, execution-safe example rather
    than one that depends on exact Levenshtein-ratio arithmetic.
    """
    existing = CanonicalProduct(
        canonical_title="Samsung Galaxy Buds 2 Pro Wireless Earbuds", brand="Samsung"
    )
    db_session.add(existing)
    await db_session.flush()

    # Same words, "2 Pro" reordered to "Pro 2" -- a common marketplace
    # listing-title variance. No model field this time -- forces fuzzy path.
    observation = _observation(
        title="Samsung Galaxy Buds Pro 2 Wireless Earbuds", brand="Samsung", model=None
    )
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "fuzzy_title"
    assert result.confidence >= 85
    assert result.canonical_product.id == existing.id


@pytest.mark.asyncio
async def test_fuzzy_match_rejects_titles_with_extra_distinguishing_words(db_session: AsyncSession) -> None:
    """Deliberately conservative: a title with a real extra qualifier
    ("Noise Cancelling") is different enough that it should NOT be merged
    into the same canonical product automatically -- favoring precision
    (no false merges) over recall at this stage of the matcher.
    """
    existing = CanonicalProduct(canonical_title="Sony WH-1000XM5 Wireless Headphones", brand="Sony")
    db_session.add(existing)
    await db_session.flush()

    observation = _observation(
        title="Sony WH1000XM5 Wireless Noise Cancelling Over-Ear Headphones",
        brand="Sony",
        model=None,
    )
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "new_canonical"
    assert result.canonical_product.id != existing.id


@pytest.mark.asyncio
async def test_no_match_creates_new_canonical_product(db_session: AsyncSession) -> None:
    observation = _observation(title="Completely Unrelated Product XYZ", brand="NoSuchBrand", model=None)
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "new_canonical"
    assert result.is_new is True
    assert result.canonical_product.id is not None
    assert result.canonical_product.canonical_title == "Completely Unrelated Product XYZ"


@pytest.mark.asyncio
async def test_fuzzy_match_does_not_cross_brands(db_session: AsyncSession) -> None:
    """A near-identical title under a different brand must not match --
    fuzzy matching is brand-scoped specifically to prevent this.
    """
    existing = CanonicalProduct(canonical_title="Wireless Headphones Model X", brand="BrandA")
    db_session.add(existing)
    await db_session.flush()

    observation = _observation(title="Wireless Headphones Model X", brand="BrandB", model=None)
    result = await resolve_canonical_product(db_session, observation)

    assert result.method == "new_canonical"
    assert result.canonical_product.id != existing.id

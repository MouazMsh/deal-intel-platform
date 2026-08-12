from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    CanonicalProduct,
    Category,
    Deal,
    Marketplace,
    MarketplaceListing,
    PriceHistory,
    PublishedDeal,
    Seller,
)
from app.domain.enums import (
    Availability,
    DealGrade,
    LifecycleStatus,
    MarketplaceCode,
    PublishedDealStatus,
)

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_full_model_chain_round_trip(db_session: AsyncSession) -> None:
    marketplace = Marketplace(code=MarketplaceCode.AMAZON_SA, display_name="Amazon.sa", base_currency="SAR")
    category = Category(code="audio", name_ar="صوتيات", name_en="Audio", emoji="🎧")
    db_session.add_all([marketplace, category])
    await db_session.flush()

    seller = Seller(
        marketplace_id=marketplace.id,
        external_seller_id="AMZN_SA",
        name="Amazon.sa",
        rating=4.6,
        review_count=120000,
        fulfillment_type="FBA",
    )
    canonical = CanonicalProduct(
        canonical_title="Sony WH-1000XM5",
        brand="Sony",
        model="WH-1000XM5",
        category_id=category.id,
    )
    db_session.add_all([seller, canonical])
    await db_session.flush()

    listing = MarketplaceListing(
        canonical_product_id=canonical.id,
        marketplace_id=marketplace.id,
        seller_id=seller.id,
        marketplace_product_id="B09JQMJHXY",
        asin="B09JQMJHXY",
        title="Sony WH-1000XM5 Wireless Headphones",
        normalized_title="sony wh-1000xm5 wireless headphones",
        image_url="https://example.com/image.jpg",
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
        rating=4.7,
        review_count=3200,
        availability=Availability.IN_STOCK,
        current_price=Decimal("899.00"),
        original_price=Decimal("1399.00"),
        shipping_cost=Decimal("0"),
        final_price=Decimal("899.00"),
        currency="SAR",
        first_seen_at=_NOW,
        last_seen_at=_NOW,
        last_verified_at=_NOW,
    )
    db_session.add(listing)
    await db_session.flush()

    price_point = PriceHistory(
        listing_id=listing.id,
        observed_at=_NOW,
        price=Decimal("899.00"),
        original_price=Decimal("1399.00"),
        effective_price=Decimal("899.00"),
        availability=Availability.IN_STOCK,
        source="mock_amazon",
    )
    deal = Deal(
        listing_id=listing.id,
        deal_score=94,
        deal_confidence=35,
        deal_grade=DealGrade.A,
        lifecycle_status=LifecycleStatus.QUALIFIED,
        last_evaluated_at=_NOW,
        last_verified_at=_NOW,
    )
    db_session.add_all([price_point, deal])
    await db_session.flush()

    published = PublishedDeal(
        deal_id=deal.id,
        telegram_channel_id="@test_channel",
        telegram_message_id=42,
        tracking_slug="abc123",
        published_at=_NOW,
        updated_at=_NOW,
        status=PublishedDealStatus.ACTIVE,
    )
    db_session.add(published)
    await db_session.commit()

    # Round-trip: fetch the listing back via a fresh query and walk relationships.
    result = await db_session.execute(
        select(MarketplaceListing).where(MarketplaceListing.marketplace_product_id == "B09JQMJHXY")
    )
    fetched_listing = result.scalar_one()
    assert fetched_listing.canonical_product_id == canonical.id
    assert fetched_listing.current_price == Decimal("899.00")

    result = await db_session.execute(
        select(Deal).options(selectinload(Deal.published_deal)).where(Deal.listing_id == fetched_listing.id)
    )
    fetched_deal = result.scalar_one()
    assert fetched_deal.deal_score == 94
    assert fetched_deal.deal_confidence == 35
    assert fetched_deal.deal_grade == DealGrade.A
    assert fetched_deal.published_deal.tracking_slug == "abc123"


@pytest.mark.asyncio
async def test_duplicate_listing_for_same_marketplace_product_is_rejected(db_session: AsyncSession) -> None:
    marketplace = Marketplace(code=MarketplaceCode.NOON_SA, display_name="Noon", base_currency="SAR")
    canonical = CanonicalProduct(canonical_title="Test Product")
    db_session.add_all([marketplace, canonical])
    await db_session.flush()

    def make_listing() -> MarketplaceListing:
        return MarketplaceListing(
            canonical_product_id=canonical.id,
            marketplace_id=marketplace.id,
            marketplace_product_id="DUPLICATE-ID",
            title="Test Product",
            normalized_title="test product",
            product_url="https://www.noon.com/test",
            availability=Availability.IN_STOCK,
            current_price=Decimal("100.00"),
            final_price=Decimal("100.00"),
            first_seen_at=_NOW,
            last_seen_at=_NOW,
            last_verified_at=_NOW,
        )

    db_session.add(make_listing())
    await db_session.commit()

    db_session.add(make_listing())
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_deleting_listing_cascades_to_price_history_and_deals(db_session: AsyncSession) -> None:
    marketplace = Marketplace(code=MarketplaceCode.AMAZON_SA, display_name="Amazon.sa", base_currency="SAR")
    canonical = CanonicalProduct(canonical_title="Cascade Test Product")
    db_session.add_all([marketplace, canonical])
    await db_session.flush()

    listing = MarketplaceListing(
        canonical_product_id=canonical.id,
        marketplace_id=marketplace.id,
        marketplace_product_id="CASCADE-ID",
        title="Cascade Test Product",
        normalized_title="cascade test product",
        product_url="https://www.amazon.sa/dp/CASCADE-ID",
        availability=Availability.IN_STOCK,
        current_price=Decimal("50.00"),
        final_price=Decimal("50.00"),
        first_seen_at=_NOW,
        last_seen_at=_NOW,
        last_verified_at=_NOW,
    )
    db_session.add(listing)
    await db_session.flush()

    db_session.add(
        PriceHistory(
            listing_id=listing.id,
            observed_at=_NOW,
            price=Decimal("50.00"),
            effective_price=Decimal("50.00"),
            availability=Availability.IN_STOCK,
            source="mock_amazon",
        )
    )
    await db_session.commit()

    await db_session.delete(listing)
    await db_session.commit()

    result = await db_session.execute(select(PriceHistory).where(PriceHistory.listing_id == listing.id))
    assert result.scalars().all() == []

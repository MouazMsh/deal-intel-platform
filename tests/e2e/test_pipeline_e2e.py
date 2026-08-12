"""Full pipeline, mock providers only -- no live Amazon/Noon involved.

Two scenarios:

1. A single fresh scan across every mock fixture from both marketplaces,
   with no seeded history -- proves the pipeline runs end-to-end without
   crashing on any fixture (including the deliberately malformed ones the
   mock providers already filter out), routes out-of-stock listings
   correctly, and resolves the Amazon/Noon Sony fixtures to the *same*
   canonical product (cross-marketplace matching).

2. A seeded-history scenario for one product, run twice, proving: (a) with
   real historical prices behind it, a genuine discount produces a
   QUALIFIED deal with a real Deal Score (not just because the marketplace
   *advertised* a discount -- the "don't trust the advertised discount"
   principle, exercised end-to-end); and (b) running the identical scan
   again immediately afterward does NOT trigger a republish (dedup/cooldown
   working across two real pipeline runs, not just in isolated unit tests).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CanonicalProduct, MarketplaceListing, PriceHistory, PublishedDeal
from app.deals.pipeline import get_or_create_marketplace, run_pipeline_for_marketplace
from app.deals.publishing import process_publishing
from app.domain.dto import RawProductObservation
from app.domain.enums import (
    Availability,
    DealGrade,
    LifecycleStatus,
    MarketplaceCode,
    PublishedDealStatus,
)
from app.matching.normalizer import normalize_title
from app.providers.amazon.mock import MockAmazonProvider
from app.providers.noon.mock import MockNoonProvider
from app.telegram.publisher import TelegramPublisher
from tests.conftest import make_settings

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_fresh_scan_across_all_fixtures_does_not_crash_and_routes_correctly(
    db_session: AsyncSession,
) -> None:
    settings = make_settings()
    amazon_provider = MockAmazonProvider()
    noon_provider = MockNoonProvider()

    amazon_observations = await amazon_provider.search_products("", limit=100)
    noon_observations = await noon_provider.search_products("", limit=100)
    assert len(amazon_observations) == 6  # 7 fixtures, 1 malformed, already filtered
    assert len(noon_observations) == 4  # 5 fixtures, 1 malformed, already filtered

    amazon_results = await run_pipeline_for_marketplace(
        db_session, settings, MarketplaceCode.AMAZON_SA, "Amazon.sa", amazon_observations, now=_NOW
    )
    noon_results = await run_pipeline_for_marketplace(
        db_session, settings, MarketplaceCode.NOON_SA, "noon", noon_observations, now=_NOW
    )

    assert len(amazon_results) == 6
    assert len(noon_results) == 4

    # Every result has a fully-populated Deal -- no partial/crashed evaluation.
    for result in amazon_results + noon_results:
        assert result.deal.deal_score is not None
        assert result.deal.deal_confidence is not None
        assert result.deal.deal_grade is not None
        assert result.deal.deal_classification is not None
        assert result.deal.lifecycle_status in {
            LifecycleStatus.QUALIFIED,
            LifecycleStatus.REJECTED,
            LifecycleStatus.OUT_OF_STOCK,
        }

    # The out-of-stock fixtures (PS5 on Amazon, Galaxy S24 Ultra on Noon)
    # must route to OUT_OF_STOCK regardless of score.
    ps5_result = next(r for r in amazon_results if r.deal.listing.marketplace_product_id == "B07OOS0001")
    assert ps5_result.deal.lifecycle_status == LifecycleStatus.OUT_OF_STOCK

    galaxy_result = next(r for r in noon_results if r.deal.listing.marketplace_product_id == "N-OOS-001")
    assert galaxy_result.deal.lifecycle_status == LifecycleStatus.OUT_OF_STOCK

    # Cross-marketplace matching: the Sony WH-1000XM5 fixture exists on both
    # Amazon and Noon with matching brand+model -- they must resolve to the
    # SAME canonical product, which is what makes an Amazon-vs-Noon price
    # comparison possible in a later phase.
    amazon_sony = next(r for r in amazon_results if "Sony" in r.deal.listing.title and "XM5" in r.deal.listing.title)
    noon_sony = next(r for r in noon_results if "Sony" in r.deal.listing.title and "XM5" in r.deal.listing.title)
    assert amazon_sony.deal.listing.canonical_product_id == noon_sony.deal.listing.canonical_product_id

    # Noon's Sony listing (849 SAR) is cheaper than Amazon's (899 SAR on the
    # non-duplicate listing) -- confirms per-marketplace prices stayed
    # distinct even though the canonical product is shared.
    assert noon_sony.deal.listing.current_price < amazon_sony.deal.listing.current_price


@pytest.mark.asyncio
async def test_seeded_history_produces_qualified_deal_then_dedup_blocks_immediate_repeat(
    db_session: AsyncSession,
) -> None:
    settings = make_settings()

    # --- Seed 25 days of real price history for the Sony listing at a
    # higher price, so the incoming mock observation (899 SAR) represents a
    # genuine discount against tracked history -- not just a
    # marketplace-advertised percentage.
    marketplace = await get_or_create_marketplace(db_session, MarketplaceCode.AMAZON_SA, "Amazon.sa")
    canonical = CanonicalProduct(canonical_title="Sony WH-1000XM5", brand="Sony", model="WH-1000XM5")
    db_session.add(canonical)
    await db_session.flush()

    listing = MarketplaceListing(
        canonical_product_id=canonical.id,
        marketplace_id=marketplace.id,
        marketplace_product_id="B09JQMJHXY",  # matches the real Amazon fixture's ID
        title="Sony WH-1000XM5 Wireless Headphones",
        normalized_title=normalize_title("Sony WH-1000XM5 Wireless Headphones"),
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
        availability=Availability.IN_STOCK,
        current_price=Decimal("1399.00"),
        original_price=Decimal("1399.00"),
        final_price=Decimal("1399.00"),
        first_seen_at=_NOW - timedelta(days=25),
        last_seen_at=_NOW - timedelta(days=5),
        last_verified_at=_NOW - timedelta(days=5),
    )
    db_session.add(listing)
    await db_session.flush()

    seed_prices = [("1399.00", 25), ("1380.00", 20), ("1350.00", 15), ("1320.00", 10), ("1300.00", 5)]
    for price_str, days_ago in seed_prices:
        db_session.add(
            PriceHistory(
                listing_id=listing.id,
                observed_at=_NOW - timedelta(days=days_ago),
                price=Decimal(price_str),
                effective_price=Decimal(price_str),
                availability=Availability.IN_STOCK,
                source="seed",
            )
        )
    await db_session.commit()

    # --- First real pipeline run: the mock Amazon fixture set includes the
    # same product ID at 899 SAR.
    amazon_provider = MockAmazonProvider()
    observations = await amazon_provider.search_products("", limit=100)
    sony_observation = next(o for o in observations if o.marketplace_product_id == "B09JQMJHXY")

    first_results = await run_pipeline_for_marketplace(
        db_session, settings, MarketplaceCode.AMAZON_SA, "Amazon.sa", [sony_observation], now=_NOW
    )
    first_result = first_results[0]

    assert first_result.deal.lifecycle_status == LifecycleStatus.QUALIFIED
    assert first_result.deal.deal_score is not None and first_result.deal.deal_score >= settings.MIN_DEAL_SCORE
    assert first_result.deal.deal_grade != DealGrade.REJECT
    assert first_result.deal.rejection_reason is None
    assert first_result.deal.first_qualified_at == _NOW
    assert first_result.should_publish is True
    assert first_result.dedup_reason == "first_time_qualified"
    # The discount is measured against real tracked history, not an
    # advertised percentage.
    assert first_result.deal.discount_pct_vs_avg30 is not None
    assert first_result.deal.discount_pct_vs_avg30 > Decimal("0")

    # --- Second run, identical inputs, same instant -- must NOT re-trigger
    # a publish: nothing meaningful changed since the first run.
    second_results = await run_pipeline_for_marketplace(
        db_session, settings, MarketplaceCode.AMAZON_SA, "Amazon.sa", [sony_observation], now=_NOW
    )
    second_result = second_results[0]

    assert second_result.deal.lifecycle_status == LifecycleStatus.QUALIFIED
    assert second_result.should_publish is False
    assert second_result.dedup_reason == "no_meaningful_change_within_cooldown"
    # Still the same Deal row (singleton per listing), not a duplicate.
    assert second_result.deal.id == first_result.deal.id


@pytest.mark.asyncio
async def test_full_publish_then_price_rises_and_post_gets_expired(db_session: AsyncSession) -> None:
    """The complete Phase 3 story end-to-end: a genuine discount publishes
    a real Telegram post, then a later scan finding the price back near
    its historical average edits that same post to an expiration notice --
    never leaving a stale "great deal" claim sitting in the channel.
    """
    settings = make_settings()
    marketplace = await get_or_create_marketplace(db_session, MarketplaceCode.AMAZON_SA, "Amazon.sa")
    canonical = CanonicalProduct(canonical_title="Sony WH-1000XM5", brand="Sony", model="WH-1000XM5")
    db_session.add(canonical)
    await db_session.flush()

    listing = MarketplaceListing(
        canonical_product_id=canonical.id,
        marketplace_id=marketplace.id,
        marketplace_product_id="B09JQMJHXY",
        title="Sony WH-1000XM5 Wireless Headphones",
        normalized_title=normalize_title("Sony WH-1000XM5 Wireless Headphones"),
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
        availability=Availability.IN_STOCK,
        current_price=Decimal("1399.00"),
        original_price=Decimal("1399.00"),
        final_price=Decimal("1399.00"),
        first_seen_at=_NOW - timedelta(days=25),
        last_seen_at=_NOW - timedelta(days=5),
        last_verified_at=_NOW - timedelta(days=5),
    )
    db_session.add(listing)
    await db_session.flush()

    for price_str, days_ago in [("1399.00", 25), ("1380.00", 20), ("1350.00", 15), ("1320.00", 10), ("1300.00", 5)]:
        db_session.add(
            PriceHistory(
                listing_id=listing.id,
                observed_at=_NOW - timedelta(days=days_ago),
                price=Decimal(price_str),
                effective_price=Decimal(price_str),
                availability=Availability.IN_STOCK,
                source="seed",
            )
        )
    await db_session.commit()

    amazon_provider = MockAmazonProvider()
    observations = await amazon_provider.search_products("", limit=100)
    sony_observation = next(o for o in observations if o.marketplace_product_id == "B09JQMJHXY")

    # --- Cycle 1: genuine discount, publish for real (mock Telegram client).
    first_results = await run_pipeline_for_marketplace(
        db_session, settings, MarketplaceCode.AMAZON_SA, "Amazon.sa", [sony_observation], now=_NOW
    )
    first_result = first_results[0]
    assert first_result.deal.lifecycle_status == LifecycleStatus.QUALIFIED

    telegram_settings = make_settings(ENVIRONMENT="development", DRY_RUN=False, TELEGRAM_TEST_CHANNEL_ID="@test")
    client = AsyncMock()
    client.send_message.return_value = 777
    publisher = TelegramPublisher(telegram_settings, client=client)

    publish_outcome = await process_publishing(db_session, publisher, first_result, now=_NOW)
    assert publish_outcome.action == "published"
    client.send_message.assert_awaited_once()

    published_row = (await db_session.execute(select(PublishedDeal))).scalars().one()
    assert published_row.status == PublishedDealStatus.ACTIVE
    assert published_row.telegram_message_id == 777

    # --- Cycle 2: the price climbs back up near its historical average --
    # a genuinely worse deal, not a marketplace discount trick.
    risen_price_observation = RawProductObservation(
        marketplace_code=MarketplaceCode.AMAZON_SA,
        marketplace_product_id="B09JQMJHXY",
        asin="B09JQMJHXY",
        title="Sony WH-1000XM5 Wireless Headphones",
        brand="Sony",
        model="WH-1000XM5",
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
        seller_external_id="AMZN_SA",
        seller_name="Amazon.sa",
        seller_rating=4.6,
        seller_review_count=120000,
        rating=4.7,
        review_count=3200,
        availability=Availability.IN_STOCK,
        price=Decimal("1390.00"),
        original_price=Decimal("1399.00"),
        currency="SAR",
        observed_at=_NOW + timedelta(days=1),
    )

    second_results = await run_pipeline_for_marketplace(
        db_session,
        settings,
        MarketplaceCode.AMAZON_SA,
        "Amazon.sa",
        [risen_price_observation],
        now=_NOW + timedelta(days=1),
    )
    second_result = second_results[0]
    # No longer qualifies, and it WAS published -- so the target is
    # PRICE_CHANGED (not REJECTED, which is reserved for "never qualified").
    assert second_result.deal.lifecycle_status == LifecycleStatus.PRICE_CHANGED
    assert second_result.deal.deal_score is not None and second_result.deal.deal_score < settings.MIN_DEAL_SCORE

    expire_outcome = await process_publishing(db_session, publisher, second_result, now=_NOW + timedelta(days=1))

    assert expire_outcome.action == "expired"
    client.edit_message_text.assert_awaited_once()
    # The edit targeted the SAME message -- never a new post for the same deal.
    edit_call_args = client.edit_message_text.call_args
    assert edit_call_args.args[1] == 777

    await db_session.refresh(published_row)
    assert published_row.status == PublishedDealStatus.EXPIRED
    assert second_result.deal.lifecycle_status == LifecycleStatus.EXPIRED
    assert second_result.deal.expired_at == _NOW + timedelta(days=1)

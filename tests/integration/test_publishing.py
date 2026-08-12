from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CanonicalProduct, Deal, Marketplace, MarketplaceListing, PublishedDeal, Seller
from app.deals.pipeline import DealEvaluationResult
from app.deals.publishing import process_publishing
from app.domain.enums import (
    Availability,
    DealGrade,
    LifecycleStatus,
    MarketplaceCode,
    PublishedDealStatus,
)
from app.telegram.publisher import TelegramPublisher
from tests.conftest import make_settings

_NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


async def _make_listing(
    db_session: AsyncSession, *, blacklisted: bool = False, seller_blacklisted: bool = False
) -> MarketplaceListing:
    marketplace = Marketplace(code=MarketplaceCode.AMAZON_SA, display_name="Amazon.sa")
    canonical = CanonicalProduct(canonical_title="Sony WH-1000XM5", brand="Sony", model="WH-1000XM5")
    db_session.add_all([marketplace, canonical])
    await db_session.flush()

    seller = Seller(
        marketplace_id=marketplace.id,
        external_seller_id="AMZN_SA",
        name="Amazon.sa",
        rating=4.6,
        review_count=120000,
        blacklisted=seller_blacklisted,
    )
    db_session.add(seller)
    await db_session.flush()

    listing = MarketplaceListing(
        canonical_product_id=canonical.id,
        marketplace_id=marketplace.id,
        seller_id=seller.id,
        marketplace_product_id="B09JQMJHXY",
        title="Sony WH-1000XM5 Wireless Headphones",
        normalized_title="sony wh1000xm5 wireless headphones",
        product_url="https://www.amazon.sa/dp/B09JQMJHXY",
        availability=Availability.IN_STOCK,
        current_price=Decimal("899.00"),
        original_price=Decimal("1399.00"),
        final_price=Decimal("899.00"),
        first_seen_at=_NOW,
        last_seen_at=_NOW,
        last_verified_at=_NOW,
        blacklisted=blacklisted,
    )
    listing.marketplace = marketplace
    listing.seller = seller
    listing.canonical_product = canonical
    db_session.add(listing)
    await db_session.flush()
    return listing


def _make_deal(listing: MarketplaceListing, *, lifecycle: LifecycleStatus, score: int = 88) -> Deal:
    deal = Deal(
        listing_id=listing.id,
        deal_score=score,
        deal_confidence=75,
        deal_grade=DealGrade.A,
        lifecycle_status=lifecycle,
        score_breakdown={
            "discount_vs_avg30": {
                "weighted_points": 30.0,
                "reason_ar": "أقل من متوسط 30 يوم",
                "reason_en": "Below the 30-day average",
            }
        },
        discount_pct_vs_avg30=Decimal("25.00"),
        last_evaluated_at=_NOW,
        last_verified_at=_NOW,
    )
    deal.listing = listing
    return deal


def _publisher(*, dry_run: bool, with_client: bool = True) -> tuple[TelegramPublisher, AsyncMock | None]:
    settings = make_settings(
        ENVIRONMENT="development",
        DRY_RUN=dry_run,
        TELEGRAM_TEST_CHANNEL_ID="@test_channel",
    )
    client = AsyncMock() if with_client else None
    if client is not None:
        client.send_message.return_value = 111
    return TelegramPublisher(settings, client=client), client


@pytest.mark.asyncio
async def test_new_qualified_deal_dry_run_does_not_persist_published_deal(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.QUALIFIED)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=True)
    result = DealEvaluationResult(deal=deal, should_publish=True, dedup_reason="first_time_qualified")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "dry_run"
    published = (await db_session.execute(select(PublishedDeal))).scalars().first()
    assert published is None
    assert deal.lifecycle_status == LifecycleStatus.QUALIFIED  # unchanged -- nothing was really published


@pytest.mark.asyncio
async def test_new_qualified_deal_real_publish_creates_published_deal(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.QUALIFIED)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=True, dedup_reason="first_time_qualified")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "published"
    assert client is not None
    client.send_message.assert_awaited_once()
    published = (await db_session.execute(select(PublishedDeal))).scalars().first()
    assert published is not None
    assert published.telegram_message_id == 111
    assert published.status == PublishedDealStatus.ACTIVE
    assert deal.lifecycle_status == LifecycleStatus.PUBLISHED
    assert deal.published_at == _NOW


@pytest.mark.asyncio
async def test_should_publish_false_takes_no_action(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.QUALIFIED)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(
        deal=deal, should_publish=False, dedup_reason="no_meaningful_change_within_cooldown"
    )

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "no_action"
    assert outcome.reason == "no_meaningful_change_within_cooldown"
    assert client is not None
    client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_blacklisted_listing_is_gate_blocked(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session, blacklisted=True)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.QUALIFIED)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=True, dedup_reason="first_time_qualified")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "gate_blocked"
    assert outcome.reason == "listing_blacklisted"
    assert deal.lifecycle_status == LifecycleStatus.REJECTED
    assert client is not None
    client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_blacklisted_seller_is_gate_blocked(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session, seller_blacklisted=True)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.QUALIFIED)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=True, dedup_reason="first_time_qualified")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "gate_blocked"
    assert outcome.reason == "seller_blacklisted"


@pytest.mark.asyncio
async def test_already_published_deal_still_qualifying_gets_updated_not_republished(
    db_session: AsyncSession,
) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.PUBLISHED)
    db_session.add(deal)
    await db_session.flush()

    existing = PublishedDeal(
        deal_id=deal.id,
        telegram_channel_id="@test_channel",
        telegram_message_id=555,
        tracking_slug="abc123",
        published_at=_NOW,
        updated_at=_NOW,
        status=PublishedDealStatus.ACTIVE,
    )
    db_session.add(existing)
    await db_session.flush()

    # Pipeline already re-determined lifecycle=QUALIFIED-target-was-a-noop;
    # simulate that here directly since this test isolates publishing.py.
    deal.lifecycle_status = LifecycleStatus.QUALIFIED

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=True, dedup_reason="significant_price_decrease")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "updated"
    assert client is not None
    client.edit_message_text.assert_awaited_once()
    client.send_message.assert_not_called()
    assert deal.lifecycle_status == LifecycleStatus.PUBLISHED

    # Still exactly one PublishedDeal row -- never a duplicate.
    all_published = (await db_session.execute(select(PublishedDeal))).scalars().all()
    assert len(all_published) == 1


@pytest.mark.asyncio
async def test_price_changed_expires_the_post(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.PRICE_CHANGED, score=40)
    db_session.add(deal)
    await db_session.flush()

    existing = PublishedDeal(
        deal_id=deal.id,
        telegram_channel_id="@test_channel",
        telegram_message_id=555,
        tracking_slug="abc123",
        published_at=_NOW,
        updated_at=_NOW,
        status=PublishedDealStatus.ACTIVE,
    )
    db_session.add(existing)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=False, dedup_reason="n/a")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "expired"
    assert client is not None
    client.edit_message_text.assert_awaited_once()
    assert existing.status == PublishedDealStatus.EXPIRED
    assert deal.lifecycle_status == LifecycleStatus.EXPIRED
    assert deal.expired_at == _NOW


@pytest.mark.asyncio
async def test_out_of_stock_marks_unavailable_but_stays_recoverable(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.OUT_OF_STOCK)
    db_session.add(deal)
    await db_session.flush()

    existing = PublishedDeal(
        deal_id=deal.id,
        telegram_channel_id="@test_channel",
        telegram_message_id=555,
        tracking_slug="abc123",
        published_at=_NOW,
        updated_at=_NOW,
        status=PublishedDealStatus.ACTIVE,
    )
    db_session.add(existing)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=False, dedup_reason="n/a")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "marked_unavailable"
    assert client is not None
    client.edit_message_text.assert_awaited_once()
    # Deliberately NOT expired -- OUT_OF_STOCK can recover.
    assert existing.status == PublishedDealStatus.ACTIVE
    assert deal.lifecycle_status == LifecycleStatus.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_rejected_deal_with_no_prior_post_takes_no_action(db_session: AsyncSession) -> None:
    listing = await _make_listing(db_session)
    deal = _make_deal(listing, lifecycle=LifecycleStatus.REJECTED, score=40)
    db_session.add(deal)
    await db_session.flush()

    publisher, client = _publisher(dry_run=False)
    result = DealEvaluationResult(deal=deal, should_publish=False, dedup_reason="n/a")

    outcome = await process_publishing(db_session, publisher, result, now=_NOW)

    assert outcome.action == "no_action"
    assert client is not None
    client.send_message.assert_not_called()
    client.edit_message_text.assert_not_called()

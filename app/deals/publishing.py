"""Orchestrates turning a DealEvaluationResult (from deals/pipeline.py)
into actual Telegram channel activity: new posts, in-place edits for price
changes / back-in-stock recovery, and expiration notices.

Kept as a separate module from pipeline.py deliberately -- the pipeline's
job is "is this a good deal and should it be published", which is pure
deal-intelligence logic and has no idea Telegram exists. This module is the
only place that translates a publish decision into an actual Telegram API
call, which is what keeps deals/pipeline.py testable without a Telegram
client at all (see tests/e2e/test_pipeline_e2e.py -- zero Telegram
involvement) and keeps this module's own tests focused on the
publish/edit/expire state machine instead of re-testing scoring.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Deal, MarketplaceListing, PublishedDeal
from app.deals.lifecycle import transition
from app.deals.pipeline import DealEvaluationResult
from app.domain.enums import DealClassification, DealGrade, LifecycleStatus, PublishedDealStatus
from app.pricing.history_service import fetch_latest_price_point
from app.telegram.formatter import DealMessageData, TelegramPost, format_deal_message, format_unavailable_message
from app.telegram.publisher import TelegramPublisher

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason: str | None = None


@dataclass(frozen=True)
class PublishOutcome:
    action: str  # "published" | "updated" | "expired" | "marked_unavailable" | "no_action" | "gate_blocked" | "dry_run"
    reason: str | None = None


def _publish_gate(deal: Deal, listing: MarketplaceListing) -> GateResult:
    """Final validation immediately before a Telegram call -- defense in
    depth on top of the pipeline's own checks (mirrors the "Post Quality"
    requirements: valid title, valid price, valid URL, not blacklisted).
    """
    if not listing.title or not listing.title.strip():
        return GateResult(False, "invalid_title")
    if listing.current_price is None or listing.current_price <= 0:
        return GateResult(False, "invalid_price")
    if not (listing.product_url.startswith("http://") or listing.product_url.startswith("https://")):
        return GateResult(False, "invalid_product_url")
    if listing.blacklisted:
        return GateResult(False, "listing_blacklisted")
    if listing.seller is not None and listing.seller.blacklisted:
        return GateResult(False, "seller_blacklisted")
    if deal.deal_score is None:
        return GateResult(False, "missing_score")
    return GateResult(True, None)


async def _build_message_data(
    session: AsyncSession, deal: Deal, listing: MarketplaceListing, *, is_back_in_stock: bool
) -> DealMessageData:
    latest = await fetch_latest_price_point(session, listing.id)
    coupon_code = latest.coupon_code if latest else None
    coupon_savings: Decimal | None = None
    if latest is not None and latest.coupon_code is not None:
        coupon_savings = latest.price - latest.effective_price

    assert deal.deal_score is not None  # enforced by _publish_gate before this is called
    return DealMessageData(
        title=listing.title,
        price=listing.current_price,
        original_price=listing.original_price,
        effective_price=listing.final_price,
        currency=listing.currency,
        coupon_code=coupon_code,
        coupon_savings=coupon_savings,
        deal_score=deal.deal_score,
        deal_confidence=deal.deal_confidence or 0,
        deal_grade=(deal.deal_grade or DealGrade.C).value,
        deal_classification=(deal.deal_classification or DealClassification.NORMAL).value,
        discount_pct_vs_avg30=deal.discount_pct_vs_avg30,
        discount_pct_vs_min=deal.discount_pct_vs_min,
        score_breakdown=deal.score_breakdown or {},
        seller_name=listing.seller.name if listing.seller else None,
        seller_rating=listing.seller.rating if listing.seller else None,
        shipping_cost=listing.shipping_cost,
        product_url=listing.product_url,
        is_back_in_stock=is_back_in_stock,
    )


async def process_publishing(
    session: AsyncSession,
    publisher: TelegramPublisher,
    result: DealEvaluationResult,
    *,
    now: datetime,
) -> PublishOutcome:
    deal = result.deal
    listing = deal.listing

    existing_result = await session.execute(select(PublishedDeal).where(PublishedDeal.deal_id == deal.id))
    published = existing_result.scalars().first()

    if deal.lifecycle_status == LifecycleStatus.QUALIFIED:
        if not result.should_publish:
            return PublishOutcome("no_action", result.dedup_reason)

        gate = _publish_gate(deal, listing)
        if not gate.passed:
            deal.lifecycle_status = transition(deal.lifecycle_status, LifecycleStatus.REJECTED)
            deal.rejection_reason = gate.reason
            await session.flush()
            logger.warning("publish_gate_blocked", extra={"listing_id": listing.id, "reason": gate.reason})
            return PublishOutcome("gate_blocked", gate.reason)

        message_data = await _build_message_data(
            session, deal, listing, is_back_in_stock=(result.dedup_reason == "back_in_stock")
        )
        post = format_deal_message(message_data)

        if published is None:
            publish_result = await publisher.publish(post)
            if publish_result.dry_run:
                return PublishOutcome("dry_run")
            published = PublishedDeal(
                deal_id=deal.id,
                telegram_channel_id=publish_result.channel_id,
                telegram_message_id=publish_result.message_id or 0,
                tracking_slug=secrets.token_urlsafe(8),
                published_at=now,
                updated_at=now,
                status=PublishedDealStatus.ACTIVE,
            )
            session.add(published)
            deal.lifecycle_status = transition(deal.lifecycle_status, LifecycleStatus.PUBLISHED)
            deal.published_at = now
            await session.flush()
            return PublishOutcome("published")

        publish_result = await publisher.update_message(published.telegram_message_id, post)
        if publish_result.dry_run:
            return PublishOutcome("dry_run")
        published.updated_at = now
        published.status = PublishedDealStatus.ACTIVE
        deal.lifecycle_status = transition(deal.lifecycle_status, LifecycleStatus.PUBLISHED)
        deal.published_at = now
        await session.flush()
        return PublishOutcome("updated", result.dedup_reason)

    if published is None or published.status != PublishedDealStatus.ACTIVE:
        return PublishOutcome("no_action")

    if deal.lifecycle_status == LifecycleStatus.PRICE_CHANGED:
        unavailable_post = format_unavailable_message(
            listing.title, listing.product_url, reason_ar="لم يعد السعر ضمن معايير الصفقة الحالية"
        )
        publish_result = await publisher.update_message(published.telegram_message_id, unavailable_post)
        if publish_result.dry_run:
            return PublishOutcome("dry_run")
        published.status = PublishedDealStatus.EXPIRED
        published.updated_at = now
        deal.lifecycle_status = transition(deal.lifecycle_status, LifecycleStatus.EXPIRED)
        deal.expired_at = now
        await session.flush()
        return PublishOutcome("expired")

    if deal.lifecycle_status == LifecycleStatus.OUT_OF_STOCK:
        unavailable_post = format_unavailable_message(
            listing.title, listing.product_url, reason_ar="نفدت الكمية حالياً"
        )
        publish_result = await publisher.update_message(published.telegram_message_id, unavailable_post)
        if publish_result.dry_run:
            return PublishOutcome("dry_run")
        # Deliberately NOT marked EXPIRED -- OUT_OF_STOCK can recover (the
        # lifecycle table allows OUT_OF_STOCK -> QUALIFIED), and a future
        # "back in stock" re-evaluation needs `published.status == ACTIVE`
        # to reach the update-in-place branch above rather than being
        # treated as a fresh, un-published deal.
        published.updated_at = now
        await session.flush()
        return PublishOutcome("marked_unavailable")

    return PublishOutcome("no_action")

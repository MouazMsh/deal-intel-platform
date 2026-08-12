"""Orchestrates one marketplace's observations through the full deal
engine: match -> record price -> score -> confidence -> grade ->
classification -> lifecycle -> dedup decision.

Scope note: this module never sets ``lifecycle_status`` to ``PUBLISHED``,
``PRICE_CHANGED``, or ``EXPIRED`` — those transitions belong to Phase 3's
Telegram publisher, which is the thing that actually knows whether a
message was sent/edited. This pipeline's job ends at producing a
``should_publish`` decision Phase 3 can act on.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import CanonicalProduct, Deal, Marketplace, MarketplaceListing, Seller
from app.deals.dedup import evaluate_republish
from app.deals.lifecycle import InvalidLifecycleTransitionError, transition
from app.domain.dto import RawProductObservation
from app.domain.enums import Availability, LifecycleStatus, MarketplaceCode
from app.matching.matcher import resolve_canonical_product
from app.matching.normalizer import normalize_title
from app.pricing.history_service import fetch_price_points, record_observation
from app.pricing.stats import compute_price_stats, pct_below, price_consistency_ratio
from app.scoring.confidence import compute_deal_confidence
from app.scoring.grade import classification_for, grade_for
from app.scoring.score import compute_deal_score

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DealEvaluationResult:
    deal: Deal
    should_publish: bool
    dedup_reason: str


async def get_or_create_marketplace(
    session: AsyncSession, code: MarketplaceCode, display_name: str
) -> Marketplace:
    result = await session.execute(select(Marketplace).where(Marketplace.code == code))
    marketplace = result.scalars().first()
    if marketplace is not None:
        return marketplace
    marketplace = Marketplace(code=code, display_name=display_name)
    session.add(marketplace)
    await session.flush()
    return marketplace


async def _get_or_create_seller(
    session: AsyncSession, marketplace: Marketplace, observation: RawProductObservation
) -> Seller | None:
    if not observation.seller_external_id:
        return None
    result = await session.execute(
        select(Seller).where(
            Seller.marketplace_id == marketplace.id,
            Seller.external_seller_id == observation.seller_external_id,
        )
    )
    seller = result.scalars().first()
    if seller is not None:
        seller.name = observation.seller_name or seller.name
        seller.rating = observation.seller_rating
        seller.review_count = observation.seller_review_count
        seller.fulfillment_type = observation.seller_fulfillment_type
        seller.marketplace = marketplace
        return seller

    seller = Seller(
        marketplace_id=marketplace.id,
        external_seller_id=observation.seller_external_id,
        name=observation.seller_name or observation.seller_external_id,
        rating=observation.seller_rating,
        review_count=observation.seller_review_count,
        fulfillment_type=observation.seller_fulfillment_type,
    )
    seller.marketplace = marketplace
    session.add(seller)
    await session.flush()
    return seller


async def _get_or_create_listing(
    session: AsyncSession,
    marketplace: Marketplace,
    canonical_product: CanonicalProduct,
    seller: Seller | None,
    observation: RawProductObservation,
    *,
    now: datetime,
) -> MarketplaceListing:
    result = await session.execute(
        select(MarketplaceListing).where(
            MarketplaceListing.marketplace_id == marketplace.id,
            MarketplaceListing.marketplace_product_id == observation.marketplace_product_id,
        )
    )
    listing = result.scalars().first()
    if listing is not None:
        listing.seller_id = seller.id if seller else listing.seller_id
        listing.title = observation.title
        listing.normalized_title = normalize_title(observation.title)
        listing.asin = observation.asin
        listing.sku = observation.sku
        listing.image_url = observation.image_url
        listing.product_url = observation.product_url
        # Wire relationships in memory explicitly rather than relying on
        # lazy-load -- under an async session, attribute access that
        # triggers an implicit SELECT raises MissingGreenlet (see
        # OPERATIONAL history: this exact class of bug was already caught
        # once in Phase 1's test suite). Every caller downstream
        # (record_observation reads listing.marketplace, tests read
        # listing.canonical_product_id, etc.) must find these pre-populated.
        listing.marketplace = marketplace
        listing.canonical_product = canonical_product
        if seller is not None:
            listing.seller = seller
        return listing

    listing = MarketplaceListing(
        canonical_product_id=canonical_product.id,
        marketplace_id=marketplace.id,
        seller_id=seller.id if seller else None,
        marketplace_product_id=observation.marketplace_product_id,
        asin=observation.asin,
        sku=observation.sku,
        title=observation.title,
        normalized_title=normalize_title(observation.title),
        image_url=observation.image_url,
        product_url=observation.product_url,
        rating=observation.rating,
        review_count=observation.review_count,
        availability=observation.availability,
        current_price=observation.price,
        original_price=observation.original_price,
        shipping_cost=observation.shipping_cost,
        final_price=observation.effective_price,
        currency=observation.currency,
        first_seen_at=now,
        last_seen_at=now,
        last_verified_at=now,
    )
    listing.marketplace = marketplace
    listing.canonical_product = canonical_product
    if seller is not None:
        listing.seller = seller
    session.add(listing)
    await session.flush()
    return listing


async def _get_or_create_deal(session: AsyncSession, listing: MarketplaceListing, *, now: datetime) -> Deal:
    result = await session.execute(select(Deal).where(Deal.listing_id == listing.id))
    deal = result.scalars().first()
    if deal is not None:
        deal.listing = listing  # ensure the in-memory relationship is wired (see note below)
        return deal
    deal = Deal(
        listing_id=listing.id,
        lifecycle_status=LifecycleStatus.DISCOVERED,
        last_evaluated_at=now,
        last_verified_at=now,
    )
    deal.listing = listing
    session.add(deal)
    await session.flush()
    return deal


def _optional_field_completeness(observation: RawProductObservation, seller: Seller | None) -> tuple[int, int]:
    optional_fields = [
        observation.rating,
        observation.review_count,
        observation.image_url,
        observation.brand,
        seller.rating if seller else None,
        seller.review_count if seller else None,
    ]
    present = sum(1 for f in optional_fields if f is not None)
    return present, len(optional_fields)


def _determine_target_lifecycle(
    current: LifecycleStatus, availability: Availability, score: int, min_deal_score: int
) -> LifecycleStatus:
    """What the lifecycle *should* be after this evaluation, given the
    current state.

    Lifecycle-aware since Phase 3: a deal already ``PUBLISHED`` (or
    ``PRICE_CHANGED``) that still qualifies must target itself again (a
    no-op via ``lifecycle.transition``'s idempotency rule) rather than
    ``QUALIFIED`` -- ``QUALIFIED`` is not a reachable transition from
    ``PUBLISHED`` (publishing is a one-way step forward; re-qualifying
    doesn't undo it). A published deal that stops qualifying targets
    ``PRICE_CHANGED``, which ``deals/publishing.py`` uses as the signal to
    edit the post and mark it expired. Every other current state uses the
    simple score-only determination from Phase 2.
    """
    if availability == Availability.OUT_OF_STOCK:
        return LifecycleStatus.OUT_OF_STOCK

    qualifies = score >= min_deal_score
    if current in (LifecycleStatus.PUBLISHED, LifecycleStatus.PRICE_CHANGED):
        return current if qualifies else LifecycleStatus.PRICE_CHANGED
    return LifecycleStatus.QUALIFIED if qualifies else LifecycleStatus.REJECTED


async def evaluate_observation(
    session: AsyncSession,
    settings: Settings,
    marketplace: Marketplace,
    observation: RawProductObservation,
    *,
    now: datetime,
) -> DealEvaluationResult:
    seller = await _get_or_create_seller(session, marketplace, observation)
    match_result = await resolve_canonical_product(session, observation)
    listing = await _get_or_create_listing(
        session, marketplace, match_result.canonical_product, seller, observation, now=now
    )

    # Capture pre-update state for the dedup decision before it's overwritten below.
    previous_availability = listing.availability
    deal = await _get_or_create_deal(session, listing, now=now)
    previous_deal_score = deal.deal_score
    previous_qualified_at = deal.first_qualified_at
    previous_had_coupon = bool(
        deal.score_breakdown and float(deal.score_breakdown.get("coupon", {}).get("contribution", 0)) > 0
    )

    await record_observation(session, listing, observation)

    points = await fetch_price_points(session, listing.id)
    stats = compute_price_stats(points, now=now)

    score_result = compute_deal_score(
        effective_price=observation.effective_price,
        price=observation.price,
        avg_30d=stats.avg_30d,
        historical_min=stats.lowest,
        seller_rating=seller.rating if seller else None,
        seller_review_count=seller.review_count if seller else None,
        seller_blacklisted=seller.blacklisted if seller else False,
        product_rating=observation.rating,
        product_review_count=observation.review_count,
        coupon_code=observation.coupon_code,
    )

    consistency_ratio = price_consistency_ratio(points)
    present_fields, total_fields = _optional_field_completeness(observation, seller)
    confidence_result = compute_deal_confidence(
        observation_count=stats.observation_count,
        history_span_days=stats.history_span_days,
        price_consistency_ratio=consistency_ratio,
        present_optional_fields=present_fields,
        total_optional_fields=total_fields,
    )

    grade = grade_for(
        score_result.score, confidence_result.confidence, min_confidence_for_grade=settings.MIN_CONFIDENCE_FOR_GRADE
    )
    discount_vs_avg30 = pct_below(observation.effective_price, stats.avg_30d) if stats.avg_30d else None
    discount_vs_min = pct_below(observation.effective_price, stats.lowest) if stats.lowest else None
    discount_advertised = None
    if observation.original_price and observation.original_price > 0:
        discount_advertised = pct_below(observation.price, observation.original_price)

    classification = classification_for(
        score_result.score,
        discount_vs_avg30,
        min_deal_score=settings.MIN_DEAL_SCORE,
        flash_deal_threshold=settings.FLASH_DEAL_THRESHOLD,
    )

    deal.deal_score = score_result.score
    deal.deal_confidence = confidence_result.confidence
    deal.deal_grade = grade
    deal.deal_classification = classification
    deal.score_breakdown = score_result.breakdown
    deal.confidence_breakdown = confidence_result.breakdown
    deal.discount_pct_advertised = discount_advertised
    deal.discount_pct_vs_avg30 = discount_vs_avg30
    deal.discount_pct_vs_min = discount_vs_min
    deal.last_evaluated_at = now
    deal.last_verified_at = observation.observed_at

    target_status = _determine_target_lifecycle(
        deal.lifecycle_status, observation.availability, score_result.score, settings.MIN_DEAL_SCORE
    )
    try:
        deal.lifecycle_status = transition(deal.lifecycle_status, target_status)
    except InvalidLifecycleTransitionError as exc:
        logger.warning(
            "lifecycle_transition_blocked",
            extra={"listing_id": listing.id, "from": deal.lifecycle_status.value, "to": target_status.value},
        )
        # Deliberately do not raise -- one listing's blocked transition must
        # not crash the batch (Phase 1 resilience principle extended here).
        _ = exc

    if deal.lifecycle_status == LifecycleStatus.QUALIFIED:
        deal.rejection_reason = None
        if deal.first_qualified_at is None:
            deal.first_qualified_at = now
    elif deal.lifecycle_status == LifecycleStatus.REJECTED:
        deal.rejection_reason = f"Score {score_result.score} below threshold {settings.MIN_DEAL_SCORE}"
    elif deal.lifecycle_status == LifecycleStatus.PRICE_CHANGED:
        # A previously-published deal that no longer clears the bar --
        # deals/publishing.py uses this state as the trigger to edit the
        # post and mark it expired, closing the Phase 2 gap flagged at the
        # time ("lifecycle table didn't yet allow PUBLISHED -> re-evaluation").
        deal.rejection_reason = f"No longer qualifies: score {score_result.score} below threshold {settings.MIN_DEAL_SCORE}"

    dedup_decision = evaluate_republish(
        previous_deal_score=previous_deal_score,
        previous_qualified_at=previous_qualified_at,
        previous_had_coupon=previous_had_coupon,
        previous_availability=previous_availability,
        previous_price=stats.previous_price,
        new_deal_score=score_result.score,
        new_price=observation.price,
        new_has_coupon=bool(observation.coupon_code),
        new_availability=observation.availability,
        now=now,
        cooldown_hours=settings.REPUBLISH_COOLDOWN_HOURS,
    )
    should_publish = deal.lifecycle_status == LifecycleStatus.QUALIFIED and dedup_decision.should_publish

    await session.flush()
    return DealEvaluationResult(deal=deal, should_publish=should_publish, dedup_reason=dedup_decision.reason)


async def run_pipeline_for_marketplace(
    session: AsyncSession,
    settings: Settings,
    marketplace_code: MarketplaceCode,
    display_name: str,
    observations: list[RawProductObservation],
    *,
    now: datetime,
) -> list[DealEvaluationResult]:
    marketplace = await get_or_create_marketplace(session, marketplace_code, display_name)
    results: list[DealEvaluationResult] = []
    for observation in observations:
        try:
            result = await evaluate_observation(session, settings, marketplace, observation, now=now)
            results.append(result)
        except Exception:  # noqa: BLE001
            # One bad observation must not crash the batch -- log with full
            # context and continue, mirroring the mock providers' own
            # per-item resilience from Phase 1.
            logger.exception(
                "observation_processing_failed",
                extra={"marketplace_product_id": observation.marketplace_product_id},
            )
    await session.commit()
    return results

"""Records price observations and fetches history for stats computation.

Every successful observation gets its own ``PriceHistory`` row — "every
meaningful price observation should be stored" per the approved
architecture — this module does not try to deduplicate identical
consecutive prices; that would throw away the exact freshness signal
(``last_verified_at``) the confidence/freshness logic depends on.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketplaceListing, PriceHistory
from app.domain.dto import RawProductObservation
from app.pricing.stats import PricePoint


async def record_observation(
    session: AsyncSession, listing: MarketplaceListing, observation: RawProductObservation
) -> PriceHistory:
    """Append a PriceHistory row and update the listing's denormalized
    current-state fields (current_price, availability, last_seen_at, ...).
    """
    price_point = PriceHistory(
        listing_id=listing.id,
        observed_at=observation.observed_at,
        price=observation.price,
        original_price=observation.original_price,
        shipping_cost=observation.shipping_cost,
        effective_price=observation.effective_price,
        coupon_code=observation.coupon_code,
        coupon_discount_value=observation.coupon_discount_value,
        coupon_discount_type=observation.coupon_discount_type,
        availability=observation.availability,
        source=listing.marketplace.code.value if listing.marketplace else "unknown",
    )
    session.add(price_point)

    listing.current_price = observation.price
    listing.original_price = observation.original_price
    listing.shipping_cost = observation.shipping_cost
    listing.final_price = observation.effective_price
    listing.availability = observation.availability
    listing.rating = observation.rating
    listing.review_count = observation.review_count
    listing.last_seen_at = observation.observed_at
    listing.last_verified_at = observation.observed_at

    await session.flush()
    return price_point


async def fetch_price_points(session: AsyncSession, listing_id: int) -> list[PricePoint]:
    """Fetch full price history for a listing, oldest first.

    Fetch-all (no window filter) is deliberate at Phase 2's data volumes —
    ``pricing/stats.py`` does the windowing (7/30/90-day) in memory. A
    cutoff-filtered query is a straightforward optimization to add later if
    a listing's history grows large enough for it to matter; not needed yet.
    """
    result = await session.execute(
        select(PriceHistory).where(PriceHistory.listing_id == listing_id).order_by(PriceHistory.observed_at)
    )
    rows = result.scalars().all()
    return [PricePoint(observed_at=row.observed_at, effective_price=row.effective_price) for row in rows]


async def fetch_latest_price_point(session: AsyncSession, listing_id: int) -> PriceHistory | None:
    """The most recent raw PriceHistory row -- used by the Telegram
    formatter (Phase 3) to display coupon details, which live on
    PriceHistory rather than on the listing or the Deal.
    """
    result = await session.execute(
        select(PriceHistory)
        .where(PriceHistory.listing_id == listing_id)
        .order_by(PriceHistory.observed_at.desc())
        .limit(1)
    )
    return result.scalars().first()

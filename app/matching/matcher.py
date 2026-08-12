"""Resolves a raw provider observation to a ``CanonicalProduct``.

Match strategy, in order (stops at the first confident match):

1. **GTIN exact** — if the observation has a GTIN/EAN/UPC and an existing
   canonical product shares it, that's as close to certain as retail data
   gets.
2. **Brand + model exact** (case-insensitive) — reliable when both fields
   are present and populated by the marketplace.
3. **Fuzzy title match** — ``rapidfuzz`` token-sort ratio against existing
   canonical titles, restricted to the same brand when a brand is known (to
   avoid matching two different brands' similarly-worded products). Only
   accepted above ``MIN_FUZZY_MATCH_CONFIDENCE``.
4. **No match** — a new ``CanonicalProduct`` is created from this
   observation.

Every outcome returns a ``MatchResult`` recording *how* the match was made
and with what confidence, stored on ``MarketplaceListing.match_method`` /
``match_confidence`` — this is what lets a human (or a later automated
check) audit a specific match rather than trusting a black box.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CanonicalProduct
from app.domain.dto import RawProductObservation
from app.matching.normalizer import normalize_title

MIN_FUZZY_MATCH_CONFIDENCE = 85


@dataclass(frozen=True)
class MatchResult:
    canonical_product: CanonicalProduct
    method: str  # "gtin_exact" | "brand_model_exact" | "fuzzy_title" | "new_canonical"
    confidence: int  # 0-100
    is_new: bool


async def resolve_canonical_product(
    session: AsyncSession, observation: RawProductObservation
) -> MatchResult:
    normalized = normalize_title(observation.title)

    if observation.gtin:
        result = await session.execute(
            select(CanonicalProduct).where(CanonicalProduct.gtin == observation.gtin)
        )
        match = result.scalars().first()
        if match is not None:
            return MatchResult(match, "gtin_exact", 100, is_new=False)

    if observation.brand and observation.model:
        result = await session.execute(
            select(CanonicalProduct).where(
                CanonicalProduct.brand.ilike(observation.brand),
                CanonicalProduct.model.ilike(observation.model),
            )
        )
        match = result.scalars().first()
        if match is not None:
            return MatchResult(match, "brand_model_exact", 95, is_new=False)

    candidates_query = select(CanonicalProduct)
    if observation.brand:
        candidates_query = candidates_query.where(CanonicalProduct.brand.ilike(observation.brand))
    result = await session.execute(candidates_query)
    candidates = result.scalars().all()

    best_candidate: CanonicalProduct | None = None
    best_score = 0
    for candidate in candidates:
        score = round(fuzz.token_sort_ratio(normalized, normalize_title(candidate.canonical_title)))
        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is not None and best_score >= MIN_FUZZY_MATCH_CONFIDENCE:
        return MatchResult(best_candidate, "fuzzy_title", best_score, is_new=False)

    new_canonical = CanonicalProduct(
        canonical_title=observation.title,
        brand=observation.brand,
        model=observation.model,
        gtin=observation.gtin,
    )
    session.add(new_canonical)
    await session.flush()  # assigns new_canonical.id without committing
    return MatchResult(new_canonical, "new_canonical", 100, is_new=True)

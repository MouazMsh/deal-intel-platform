"""Deterministic "why is this a deal?" explanation.

Reads directly from ``score_breakdown`` (the same dict stored on the
``Deal`` row) — the explanation cannot disagree with the score because it
is derived from the exact same numbers, not a second interpretation of
them. No AI call, no free-text generation.
"""

from __future__ import annotations

# A factor only makes it into the explanation if its weighted contribution
# clears this bar -- otherwise a factor contributing 1/100th of a point
# would clutter the explanation with noise.
MATERIAL_WEIGHTED_POINTS_THRESHOLD = 3.0


def build_explanation(score_breakdown: dict[str, dict[str, object]], *, lang: str = "ar") -> list[str]:
    reason_key = "reason_ar" if lang == "ar" else "reason_en"

    material_factors = [
        (name, entry)
        for name, entry in score_breakdown.items()
        if float(entry["weighted_points"]) >= MATERIAL_WEIGHTED_POINTS_THRESHOLD and entry[reason_key]
    ]
    material_factors.sort(key=lambda item: float(item[1]["weighted_points"]), reverse=True)

    return [str(entry[reason_key]) for _name, entry in material_factors]

"""Agent 2 delisting engine — a PURE deterministic rules engine, NO LLM.

Decides whether a product should leave the catalogue and HOW, using:
  - `rules.DELIST_TIERS` on the trustworthy rating + genuine-review volume, and
  - the dominant buyer-complaint cluster to ROUTE the outcome:
        possible_fraud     -> suspend      (fair, proportional seller-rating penalty)
        fabric/size (fixable) / other -> correction_window (proportional penalty; a fix draft follows)
        damaged_delivery   -> logistics_referral  (a HUB fault -> NO seller-rating penalty)

Fairness (ASSUMPTIONS §4): the seller hit is `risk_checks.seller_rating_impact` (proportional
to the failed product's share of the seller's genuine reviews, capped 0.5) — never a flat penalty;
logistics faults never touch the seller's integrity score.

`classify_complaints` is a deterministic keyword classifier: it lets the whole audit route
correctly with ZERO model calls (Agent 2's `cluster_reviews` is the richer LLM version layered on
top). This module commits nothing — the caller (the /audit router) persists actions.
"""
from __future__ import annotations

from collections import Counter

from ..models import Product
from . import risk_checks
from .rules import (
    BAN_RATING,
    DELIST_TIERS,
    FIXABLE_CLUSTERS,
    NEGATIVE_REVIEW_MAX_RATING,
    REPEAT_CASE_COUNT,
)

# Deterministic keyword buckets (checked fraud-first, then damage, then material, then size).
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("possible_fraud", ("fake", "counterfeit", "scam", "fraud", "not genuine", "not as described",
                        "never delivered", "stopped working", "never worked", "not the advertised")),
    ("damaged_delivery", ("broken", "damage", "shattered", "crushed", "in transit", "courier",
                          "mishandled", "wrong item", "torn", "destroyed", "cracked")),
    ("fabric_mismatch", ("fabric", "cotton", "polyester", "synthetic", "material", "shrank",
                         "shrunk", "faded", "cheap material", "not breathable", "rayon", "crepe",
                         "transparent", "see-through", "see through", "sheer", "thin cloth")),
    ("size_issue", ("size", "fit ", "fits", "runs small", "runs large", "too small", "too large",
                    "size chart", "tight", "loose", "measurement")),
]


def _label_for(text: str) -> str:
    t = text.lower()
    for label, kws in _KEYWORDS:
        if any(kw in t for kw in kws):
            return label
    return "other"


def _negative_reviews(product: Product) -> list:
    return [r for r in product.reviews if r.rating <= NEGATIVE_REVIEW_MAX_RATING]


def classify_complaints(product: Product) -> dict:
    """Deterministic dominant-complaint classifier over negative reviews (keyword buckets).

    Returns {dominant, agreement, counts, negative_count}. `agreement` = the dominant
    cluster's share of negative reviews. Used to ROUTE a delist without a model call."""
    negatives = _negative_reviews(product)
    total = len(negatives)
    if total == 0:
        return {"dominant": None, "agreement": 0.0, "counts": {}, "negative_count": 0}
    counts = Counter(_label_for(r.text) for r in negatives)
    label, n = counts.most_common(1)[0]
    return {
        "dominant": label,
        "agreement": round(n / total, 3),
        "counts": dict(counts),
        "negative_count": total,
    }


def delist_tier(rating: float | None, count: int) -> int | None:
    """Most-severe DELIST_TIERS index tripped, or None. Tiers run lenient->severe;
    the lowest tier (<=1.0) is inclusive of 1.0 (comment in rules.py)."""
    if rating is None:
        return None
    worst = None
    for i, (rating_below, min_count) in enumerate(DELIST_TIERS):
        below = rating <= rating_below if rating_below <= 1.0 else rating < rating_below
        if below and count >= min_count:
            worst = i
    return worst


def evaluate_delisting(product: Product, dominant_label: str | None = None) -> dict:
    """Decide the delist outcome for one product. PURE — reads the product/seller, commits
    nothing. Pass `dominant_label` to route (defaults to the deterministic classifier).

    Returns {product_id, trustworthy_rating, review_count, tier, tier_label, delist,
    action, dominant_label, agreement, seller_penalty, reason}.
    `action` ∈ keep | suspend | correction_window | logistics_referral.
    """
    tr = risk_checks.trustworthy_rating(product)
    rating = tr["trustworthy_rating"] if tr["sufficient"] else None
    count = tr["trustworthy_review_count"]
    tier = delist_tier(rating, count)

    complaints = classify_complaints(product)
    if dominant_label is None:
        dominant_label = complaints["dominant"]
    agreement = complaints["agreement"]

    seller = product.seller
    repeat_offender = bool(seller and (seller.case_count or 0) >= REPEAT_CASE_COUNT)

    base = {
        "product_id": product.id,
        "trustworthy_rating": rating,
        "review_count": count,
        "tier": tier,
        "tier_label": None if tier is None else f"<{DELIST_TIERS[tier][0]}/{DELIST_TIERS[tier][1]}+",
        "dominant_label": dominant_label,
        "agreement": agreement,
    }

    if tier is None:
        return {**base, "delist": False, "action": "keep", "seller_penalty": None,
                "reason": (f"trustworthy {rating} over {count} genuine reviews — no delist tier tripped"
                           if rating is not None else
                           f"insufficient genuine reviews ({count}) — cannot delist on thin data")}

    # ---- a tier tripped: route by dominant complaint ----
    is_fraud = dominant_label == "possible_fraud" or repeat_offender or (
        rating is not None and rating <= BAN_RATING and repeat_offender
    )

    if is_fraud:
        penalty = risk_checks.seller_rating_impact(seller, product) if seller else None
        return {**base, "delist": True, "action": "suspend", "seller_penalty": penalty,
                "reason": (f"trustworthy {rating}/{count} trips tier {base['tier_label']}; dominant "
                           f"complaint '{dominant_label}'"
                           + (" + repeat-offender seller" if repeat_offender else "")
                           + " -> suspend")}

    if dominant_label == "damaged_delivery":
        # a logistics fault, not the seller's listing -> refer to logistics, NO seller penalty.
        return {**base, "delist": True, "action": "logistics_referral", "seller_penalty": None,
                "reason": (f"trustworthy {rating}/{count} trips tier {base['tier_label']}; dominant "
                           f"complaint '{dominant_label}' is a delivery fault -> logistics referral "
                           f"(no seller-rating impact)")}

    # fixable (fabric/size) or 'other' -> a correction window; a fix draft follows for fixable.
    penalty = risk_checks.seller_rating_impact(seller, product) if seller else None
    fixable = dominant_label in FIXABLE_CLUSTERS
    return {**base, "delist": True, "action": "correction_window", "seller_penalty": penalty,
            "fixable": fixable,
            "reason": (f"trustworthy {rating}/{count} trips tier {base['tier_label']}; dominant "
                       f"complaint '{dominant_label}' -> correction window"
                       + (" + fix draft" if fixable else ""))}

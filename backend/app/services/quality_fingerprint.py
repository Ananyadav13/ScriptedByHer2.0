"""Quality-fingerprint diff — PURE deterministic comparison, NO LLM.

WHY THIS EXISTS
---------------
A seller films ONE listing video but sells the garment in several colourways. The old media
check compared the buyer's dispute video against the listing video directly, so a buyer
disputing the BLUE kurti against a video of the BLACK one produced "different colour ->
different product -> mismatch". That is a FALSE FLAG on an honest seller, and it also buries
the buyer's real complaint (the fabric).

The fix: the listing video is distilled once into the attributes every colourway physically
shares (`rules.QUALITY_INVARIANT_ATTRS` — the "golden fields": weave, sheen, texture, opacity,
stitch, drape, embellishment type). A dispute is judged against those.

The guarantee lives HERE, not in the prompt. The vision model returns a structured read of
both sides; this module decides what counts. Variant-specific attributes (colour/shade/
print colourway) are dropped before any share is computed, so even a model that insists
"the colour is completely different" cannot move the mismatch verdict. Prompts drift and
models get swapped; this arithmetic does not.

Colour is not permanently blind: a buyer whose complaint IS "wrong colour sent" is heard via
`colour_note` (see `rules.COLOUR_SENSITIVE_CLAIMS`), reported SEPARATELY from the material
mismatch so the two can never be confused for one another.
"""
from __future__ import annotations

from .rules import (
    COLOUR_SENSITIVE_CLAIMS,
    MIN_COMPARABLE_ATTRS,
    QUALITY_DIVERGENCE_SHARE,
    QUALITY_INVARIANT_ATTRS,
    VARIANT_SPECIFIC_ATTRS,
)

_UNKNOWN = {"", "unknown", "unclear", "not visible", "n/a", "none given", "indeterminate"}


def _norm(value) -> str | None:
    """Normalise one attribute reading. None => unreadable, so it is not compared."""
    if value is None:
        return None
    v = str(value).strip().lower()
    return None if v in _UNKNOWN else v


def _agrees(a: str, b: str) -> bool:
    """Two readings of the same attribute agree if either contains the other.

    Vision models describe the same thing at different lengths ("matte" vs "matte, fibrous
    finish"); substring containment absorbs that without pretending to be a semantic model.
    """
    return a == b or a in b or b in a


def compare_fingerprints(reference: dict | None, observed: dict | None,
                         claim_type: str | None = None) -> dict:
    """Diff a buyer's observed attributes against the product's golden fields.

    ONLY `rules.QUALITY_INVARIANT_ATTRS` are compared. Variant-specific attributes are
    recorded in `ignored_attributes` for the trace and never scored.

    Returns {comparable, compared_attributes, diverged, agreed, divergence_share,
    mismatch, ignored_attributes, colour_note, reason}.
    """
    if not reference or not observed:
        return {
            "comparable": False,
            "compared_attributes": [],
            "diverged": [],
            "agreed": [],
            "divergence_share": 0.0,
            "mismatch": False,
            "ignored_attributes": [],
            "colour_note": None,
            "reason": ("no quality fingerprint on the listing — cannot compare"
                       if not reference else
                       "no readable attributes in the buyer's media — cannot compare"),
        }

    compared: list[str] = []
    diverged: list[str] = []
    agreed: list[str] = []
    for attr in QUALITY_INVARIANT_ATTRS:
        ref, obs = _norm(reference.get(attr)), _norm(observed.get(attr))
        if ref is None or obs is None:
            continue  # unreadable on one side -> not evidence either way
        compared.append(attr)
        (agreed if _agrees(ref, obs) else diverged).append(attr)

    # Variant-specific readings are dropped BEFORE any scoring — this is the false-flag
    # safeguard, and it holds whatever the model reported.
    ignored = [
        a for a in VARIANT_SPECIFIC_ATTRS
        if _norm(reference.get(a)) is not None and _norm(observed.get(a)) is not None
    ]

    # A buyer complaining about the colour itself still gets colour looked at — separately,
    # so it can never be mistaken for a material mismatch.
    colour_note = None
    if claim_type in COLOUR_SENSITIVE_CLAIMS:
        ref_c, obs_c = _norm(reference.get("colour")), _norm(observed.get("colour"))
        if ref_c and obs_c and not _agrees(ref_c, obs_c):
            colour_note = (f"buyer's complaint is about colour: listing reference shows {ref_c!r}, "
                           f"buyer's media shows {obs_c!r} (reported separately — NOT counted as "
                           f"a material mismatch)")

    if len(compared) < MIN_COMPARABLE_ATTRS:
        return {
            "comparable": False,
            "compared_attributes": compared,
            "diverged": diverged,
            "agreed": agreed,
            "divergence_share": 0.0,
            "mismatch": False,
            "ignored_attributes": ignored,
            "colour_note": colour_note,
            "reason": (f"only {len(compared)} readable quality attribute(s) "
                       f"(need >= {MIN_COMPARABLE_ATTRS}) -> too thin to compare"),
        }

    share = len(diverged) / len(compared)
    mismatch = share >= QUALITY_DIVERGENCE_SHARE
    return {
        "comparable": True,
        "compared_attributes": compared,
        "diverged": diverged,
        "agreed": agreed,
        "divergence_share": round(share, 2),
        "mismatch": mismatch,
        "ignored_attributes": ignored,
        "colour_note": colour_note,
        "reason": (
            f"{len(diverged)}/{len(compared)} invariant quality attributes diverge "
            f"({share:.0%} >= {QUALITY_DIVERGENCE_SHARE:.0%}): {', '.join(diverged)}"
            if mismatch else
            f"{len(diverged)}/{len(compared)} invariant quality attributes diverge "
            f"({share:.0%} < {QUALITY_DIVERGENCE_SHARE:.0%}) -> consistent with the listing"
        ) + (f"; ignored variant-specific: {', '.join(ignored)}" if ignored else ""),
    }


def variant_context(product, order) -> dict:
    """Is this dispute a CROSS-VARIANT comparison (buyer's colourway != the filmed one)?

    Drives the instruction sent to the vision model and, more importantly, explains in the
    trace WHY colour was ignored — so a reviewer sees the reasoning rather than a silent drop.
    """
    variants = list(getattr(product, "variants", None) or [])
    ref = next((v for v in variants if v.is_listing_reference), None)
    ordered = None
    if order is not None and getattr(order, "variant_id", None):
        ordered = next((v for v in variants if v.id == order.variant_id), None)

    cross = bool(ref and ordered and ref.id != ordered.id)
    return {
        "has_variants": bool(variants),
        "variant_count": len(variants),
        "listing_video_variant": ref.name if ref else None,
        "ordered_variant": ordered.name if ordered else None,
        "cross_variant": cross,
        "reason": (
            f"listing video shows the {ref.name!r} variant but the buyer ordered {ordered.name!r} — "
            f"colour/shade differences are EXPECTED and are excluded from the material comparison"
            if cross else
            f"buyer's variant {ordered.name!r} is the one the listing video shows"
            if ref and ordered else
            "no variant recorded for this order — comparing on invariant quality attributes only"
        ),
    }

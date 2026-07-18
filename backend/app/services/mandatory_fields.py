"""Mandatory listing-fields gate — PURE, NO LLM (catalog gate + new-listing flow).

A listing (or a proposed new one) must carry the mandatory fields before it can go/stay
live: a size chart (sized categories), a fabric/material claim (textile categories), and the
seller's LISTING VIDEO (the canonical media reference — ASSUMPTIONS §8). A live listing that
is missing them is HELD (`needs_info`); a new listing that is missing them is BLOCKED.

The field set is category-aware so we don't demand a size chart on a coffee mug. It is also
CONTENT-aware: a size chart that is present but measurement-free (`{"Free Size": "Free Size"}`)
counts as missing, because it leaves the buyer exactly as blind as no chart at all.
"""
from __future__ import annotations

from .rules import MANDATORY_FIELDS

# categories for which each conditional field is actually required.
_SIZED = {"apparel", "footwear"}
# Categories sold as "Free Size" but whose returns are driven by SIZE anyway — a bag or a
# jewellery set has no S/M/L, yet a buyer still needs L x W x H to know what turns up. These
# carry their measurements in `size_chart_json` just like a sized category does.
_DIMENSIONED = {"accessories"}
_TEXTILE = {"apparel", "home"}
_ALWAYS = {"listing_video_path"}  # the listing video is the canonical media reference — always required

# Placeholder size labels that carry no information on their own.
_VACUOUS_LABELS = {"free size", "one size", "standard", "regular", "default", "n/a"}


def _requires_size_chart(category: str) -> bool:
    return "size_chart_json" in MANDATORY_FIELDS and category in (_SIZED | _DIMENSIONED)


def _required_fields(category: str) -> list[str]:
    req = list(_ALWAYS)
    if _requires_size_chart(category):
        req.append("size_chart_json")
    if "fabric_claim" in MANDATORY_FIELDS and category in _TEXTILE:
        req.append("fabric_claim")
    return req


def _is_vacuous_size_chart(chart) -> bool:
    """True when a size chart is present but says nothing measurable.

    `{"Free Size": "Free Size"}` satisfies a naive presence check while telling the buyer
    exactly nothing — it is the listing gap behind "good quality but small size" complaints
    on bags. A chart counts as real when ANY entry carries a digit (a measurement), e.g.
    `{"Free Size": "L 30cm x W 12cm x H 26cm"}` or `{"M": "38"}`.
    """
    if not isinstance(chart, dict) or not chart:
        return True
    for label, value in chart.items():
        if any(ch.isdigit() for ch in str(value)):
            return False
        if str(label).strip().lower() not in _VACUOUS_LABELS:
            return False
    return True


def _missing(fields: dict, category: str) -> list[str]:
    missing = []
    for f in _required_fields(category):
        val = fields.get(f)
        if val is None or (isinstance(val, (str, list, dict)) and len(val) == 0):
            missing.append(f)
        elif f == "size_chart_json" and _is_vacuous_size_chart(val):
            # present but measurement-free -> as useless to the buyer as absent
            missing.append(f)
    return missing


def check_product(product) -> dict:
    """Gate an existing product. Returns {complete, missing, required, reason}."""
    fields = {
        "size_chart_json": product.size_chart_json,
        "fabric_claim": product.fabric_claim,
        "listing_video_path": product.listing_video_path,
    }
    missing = _missing(fields, product.category)
    return {
        "product_id": product.id,
        "category": product.category,
        "required": _required_fields(product.category),
        "missing": missing,
        "complete": not missing,
        "reason": ("all mandatory fields present" if not missing
                   else f"missing mandatory field(s): {', '.join(missing)}"),
    }


# A NEW listing must also carry the basic product-description fields — a listing is more than
# the three trust-critical media fields. These are gated ONLY on creation (check_new_listing),
# NOT on already-live products (check_product), so existing seed products aren't retro-flagged.
_NEW_LISTING_DESCRIPTIVE = ("title", "description", "color")
_MIN_DESCRIPTION_LEN = 20  # a one-word "nice" description helps nobody


def _new_listing_required(category: str) -> list[str]:
    return list(_NEW_LISTING_DESCRIPTIVE) + _required_fields(category)


def check_new_listing(payload: dict) -> dict:
    """Gate a proposed NEW listing (seller flow). Beyond the trust-critical media
    fields, a new listing must carry a title, a real description, and a colour. `payload`
    carries category + all fields. Returns {allowed, missing, required, reason}."""
    category = payload.get("category", "")
    missing = _missing(payload, category)  # conditional media/size/fabric fields
    for f in _NEW_LISTING_DESCRIPTIVE:
        val = payload.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(f)
        elif f == "description" and len(str(val).strip()) < _MIN_DESCRIPTION_LEN:
            missing.append(f)  # present but too thin to be a real description
    # stable order: descriptive fields first, then the media/size gate
    order = {f: i for i, f in enumerate(_new_listing_required(category))}
    missing = sorted(set(missing), key=lambda f: order.get(f, 99))
    return {
        "category": category,
        "required": _new_listing_required(category),
        "missing": missing,
        "allowed": not missing,
        "reason": ("listing meets the mandatory-field gate" if not missing
                   else f"listing blocked — provide: {', '.join(missing)}"),
    }

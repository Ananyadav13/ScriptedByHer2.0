"""Mandatory listing-fields gate — PURE, NO LLM (Phase 4 gate; Phase 5 new-listing flow).

A listing (or a proposed new one) must carry the mandatory fields before it can go/stay
live: a size chart (sized categories), a fabric/material claim (textile categories), and the
seller's LISTING VIDEO (the canonical media reference — ASSUMPTIONS §8). A live listing that
is missing them is HELD (`needs_info`); a new listing that is missing them is BLOCKED.

The field set is category-aware so we don't demand a size chart on a coffee mug.
"""
from __future__ import annotations

from .rules import MANDATORY_FIELDS

# categories for which each conditional field is actually required.
_SIZED = {"apparel", "footwear"}
_TEXTILE = {"apparel", "home"}
_ALWAYS = {"listing_video_path"}  # the listing video is the canonical media reference — always required


def _required_fields(category: str) -> list[str]:
    req = list(_ALWAYS)
    if "size_chart_json" in MANDATORY_FIELDS and category in _SIZED:
        req.append("size_chart_json")
    if "fabric_claim" in MANDATORY_FIELDS and category in _TEXTILE:
        req.append("fabric_claim")
    return req


def _missing(fields: dict, category: str) -> list[str]:
    missing = []
    for f in _required_fields(category):
        val = fields.get(f)
        if val is None or (isinstance(val, (str, list, dict)) and len(val) == 0):
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


def check_new_listing(payload: dict) -> dict:
    """Gate a proposed NEW listing (Phase 5 seller flow). `payload` carries category +
    the mandatory fields. Returns {allowed, missing, required, reason}."""
    category = payload.get("category", "")
    missing = _missing(payload, category)
    return {
        "category": category,
        "required": _required_fields(category),
        "missing": missing,
        "allowed": not missing,
        "reason": ("listing meets the mandatory-field gate" if not missing
                   else f"listing blocked — provide: {', '.join(missing)}"),
    }

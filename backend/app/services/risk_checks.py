"""Deterministic risk checks — plain functions, NO LLM (PLAN.md §5, PHASES.md Phase 2).

Each returns a JSON-serializable dict with concrete numbers + a boolean `flag`,
so the agent (and the SSE trace) can cite the exact evidence.

Design rules encoded here (from the idea deck):
- A branded listing priced far below MRP is a counterfeit signal.
- A review burst only counts as fake-review evidence when the spike coincides
  with a high share of brand-new accounts — an honest viral seller (real,
  old accounts) must never be flagged.
- Delivery fast-track needs TWO independent signals; serial claimers get routed
  to manual review, not auto-refunded.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

# ---- thresholds (single source of truth; Phase 4 tests pin these) ----
PRICE_BELOW_MRP_RATIO = 0.35      # price < 35% of MRP on a branded item -> suspicious
NEW_ACCOUNT_AGE_DAYS = 30         # "brand new" reviewer account
BURST_MIN_PEAK = 8                # >= this many reviews on one day = a spike
BURST_NEW_SHARE = 0.5             # AND >= this share from new accounts -> fake-burst flag
SERIAL_CLAIM_COUNT = 5            # claim_history count >= this -> serial claimer


def price_mrp_risk(product) -> dict:
    """Branded product priced far below its MRP -> counterfeit signal."""
    mrp = product.mrp or 0
    ratio = (product.price / mrp) if mrp else 1.0
    branded = bool(product.brand) and product.brand.strip() != ""
    flag = branded and mrp > 0 and ratio < PRICE_BELOW_MRP_RATIO
    return {
        "price": product.price,
        "mrp": product.mrp,
        "price_to_mrp_ratio": round(ratio, 4),
        "brand": product.brand,
        "flag": flag,
        "reason": (
            f"{product.brand} priced at {ratio:.2%} of MRP (< {PRICE_BELOW_MRP_RATIO:.0%})"
            if flag else "price within normal range for MRP"
        ),
    }


def image_match_risk(product) -> dict:
    """Perceptual-hash match of listing images vs official reference images.

    Reference images (`media/official_images/`) are added in Phase 3, so today
    this reports `available: False` and never flags — counterfeit detection in
    Phase 2 stands on price + review-burst + seller signals. The interface is
    stable so Phase 3 only fills in the hash comparison.
    """
    return {
        "available": False,
        "flag": False,
        "reason": "no official reference images yet (perceptual-hash match lands in Phase 3)",
    }


def review_burst_risk(product) -> dict:
    """Fake-review-burst detector.

    Flags ONLY when a daily spike coincides with a high share of brand-new
    accounts. High volume from established accounts (honest viral) is NOT flagged.
    """
    reviews = list(product.reviews)
    total = len(reviews)
    if total == 0:
        return {"total_reviews": 0, "flag": False, "reason": "no reviews"}

    per_day = Counter(r.created_at.date() for r in reviews)
    peak_day_count = max(per_day.values())
    active_days = len(per_day)
    mean_daily = total / active_days
    burst_ratio = peak_day_count / mean_daily  # 1.0 == perfectly uniform

    new_accounts = sum(1 for r in reviews if r.reviewer_account_age_days < NEW_ACCOUNT_AGE_DAYS)
    new_share = new_accounts / total

    spike = peak_day_count >= BURST_MIN_PEAK
    flag = spike and new_share >= BURST_NEW_SHARE
    return {
        "total_reviews": total,
        "peak_day_count": peak_day_count,
        "burst_ratio": round(burst_ratio, 2),
        "new_account_share": round(new_share, 2),
        "flag": flag,
        "reason": (
            f"{peak_day_count} reviews in one day, {new_share:.0%} from accounts "
            f"< {NEW_ACCOUNT_AGE_DAYS}d old -> coordinated fake burst"
            if flag else
            f"volume spike but {new_share:.0%} new accounts -> looks organic (honest viral)"
            if spike else
            "no significant review spike"
        ),
    }


def seller_profile(seller) -> dict:
    """Seller trust snapshot."""
    age_days = (datetime.utcnow() - seller.account_created_at).days
    flags = list(seller.trust_flags or [])
    new_account = age_days < 90 or "new_account_cluster" in flags
    return {
        "seller_id": seller.id,
        "name": seller.name,
        "rating": seller.rating,
        "account_age_days": age_days,
        "trust_flags": flags,
        "classification": "suspicious_new" if new_account else "established",
        "flag": new_account or bool(flags),
        "reason": (
            f"account {age_days}d old; flags={flags or 'none'}"
        ),
    }


def _classify_claimer(claim_count: int) -> str:
    if claim_count >= SERIAL_CLAIM_COUNT:
        return "serial"
    if claim_count >= 1:
        return "occasional"
    return "first_time"


def delivery_signals(order, buyer) -> dict:
    """Post-delivery corroboration signals for a dispute.

    Independent signals: OTP-scan-vs-items mismatch, hub anomaly. Serial-claimer
    history is a routing signal (-> manual review), not a corroboration signal.
    """
    otp_mismatch = order.otp_scan_count < order.items_count
    hub_anomaly = bool(order.hub_anomaly_flag)
    claim_count = (buyer.claim_history or {}).get("count", 0) if buyer else 0
    claimer = _classify_claimer(claim_count)

    independent_signals = []
    if otp_mismatch:
        independent_signals.append("otp_scan_mismatch")
    if hub_anomaly:
        independent_signals.append("hub_anomaly")

    return {
        "order_id": order.id,
        "otp_scan_count": order.otp_scan_count,
        "items_count": order.items_count,
        "otp_mismatch": otp_mismatch,
        "hub_anomaly": hub_anomaly,
        "claimer_classification": claimer,
        "independent_signal_count": len(independent_signals),
        "independent_signals": independent_signals,
        "flag": len(independent_signals) >= 1,
        "reason": (
            f"{len(independent_signals)} independent signal(s): {independent_signals or 'none'}; "
            f"buyer is a {claimer} claimer (count={claim_count})"
        ),
    }

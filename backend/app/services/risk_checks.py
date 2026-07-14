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

from .rules import (
    BURST_MIN_PEAK,
    BURST_NEW_SHARE,
    HUB_ESCALATE_CASE_COUNT,
    MIN_TRUSTWORTHY_REVIEWS,
    NEW_ACCOUNT_AGE_DAYS,
    PRICE_BELOW_MRP_RATIO,
    RECENT_REVIEW_WEIGHT,
    RECENT_REVIEW_WINDOW_DAYS,
    REFUND_MIN_SIGNALS,
    REPEAT_CASE_COUNT,
    SERIAL_CLAIM_COUNT,
    OLD_REVIEW_WEIGHT,
)


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


def trustworthy_rating(product) -> dict:
    """The ONLY satisfaction measure used for decisions.

    Recency-weighted average rating that DISCOUNTS the manipulable cluster
    (reviews from brand-new accounts) to zero — so fake 5-star bursts can't buy
    a good score, and genuine buyers of a cheap knockoff can still vouch for it.
    """
    reviews = list(product.reviews)
    now = datetime.utcnow()
    weighted_sum = 0.0
    weight_total = 0.0
    counted = 0
    for r in reviews:
        if r.reviewer_account_age_days < NEW_ACCOUNT_AGE_DAYS:
            continue  # discount fake/new-account cluster entirely
        age_days = (now - r.created_at).days
        w = RECENT_REVIEW_WEIGHT if age_days <= RECENT_REVIEW_WINDOW_DAYS else OLD_REVIEW_WEIGHT
        weighted_sum += r.rating * w
        weight_total += w
        counted += 1

    if counted < MIN_TRUSTWORTHY_REVIEWS:
        return {
            "trustworthy_rating": None,
            "trustworthy_review_count": counted,
            "sufficient": False,
            "reason": (
                f"only {counted} review(s) from established accounts "
                f"(need >= {MIN_TRUSTWORTHY_REVIEWS}) -> no genuine satisfaction signal"
            ),
        }
    rating = round(weighted_sum / weight_total, 2)
    return {
        "trustworthy_rating": rating,
        "trustworthy_review_count": counted,
        "sufficient": True,
        "reason": (
            f"recency-weighted rating {rating} over {counted} established-account "
            f"reviews (new-account reviews discounted)"
        ),
    }


def seller_profile(seller) -> dict:
    """Seller trust snapshot, including repeat-offender case count."""
    age_days = (datetime.utcnow() - seller.account_created_at).days
    flags = list(seller.trust_flags or [])
    new_account = age_days < 90 or "new_account_cluster" in flags
    repeat_offender = (seller.case_count or 0) >= REPEAT_CASE_COUNT
    return {
        "seller_id": seller.id,
        "name": seller.name,
        "rating": seller.rating,
        "account_age_days": age_days,
        "trust_flags": flags,
        "case_count": seller.case_count or 0,
        "repeat_offender": repeat_offender,
        "already_banned": bool(seller.banned),
        "classification": "suspicious_new" if new_account else "established",
        "flag": new_account or bool(flags) or repeat_offender,
        "reason": (
            f"account {age_days}d old; rating {seller.rating}; "
            f"cases={seller.case_count or 0} (repeat={repeat_offender}); flags={flags or 'none'}"
        ),
    }


def _classify_claimer(claim_count: int) -> str:
    if claim_count >= SERIAL_CLAIM_COUNT:
        return "serial"
    if claim_count >= 1:
        return "occasional"
    return "first_time"


def delivery_signals(order, buyer, hub=None) -> dict:
    """Post-delivery corroboration signals for a dispute (OTP is ONE signal, not proof).

    Independent corroborating signals: OTP-scan-vs-items mismatch, hub anomaly, and
    a missing geo-tagged proof-of-delivery photo. Two or more -> refund fast-track.
    Serial-claimer history is a routing signal (-> manual review), not corroboration.
    A fraudulent hub (repeat cases) demands IMMEDIATE ops escalation.
    """
    otp_mismatch = order.otp_scan_count < order.items_count
    hub_anomaly = bool(order.hub_anomaly_flag)
    no_geo_proof = not bool(order.geo_photo_verified)
    claim_count = (buyer.claim_history or {}).get("count", 0) if buyer else 0
    claimer = _classify_claimer(claim_count)

    independent_signals = []
    if otp_mismatch:
        independent_signals.append("otp_scan_mismatch")
    if hub_anomaly:
        independent_signals.append("hub_anomaly")
    if no_geo_proof:
        independent_signals.append("no_geo_verified_photo")

    hub_case_count = (hub.case_count if hub else 0) or 0
    hub_fraudulent = hub_case_count >= HUB_ESCALATE_CASE_COUNT

    return {
        "order_id": order.id,
        "otp_scan_count": order.otp_scan_count,
        "items_count": order.items_count,
        "otp_mismatch": otp_mismatch,
        "hub_anomaly": hub_anomaly,
        "geo_photo_verified": bool(order.geo_photo_verified),
        "hub_id": order.hub_id,
        "hub_case_count": hub_case_count,
        "hub_fraudulent": hub_fraudulent,
        "claimer_classification": claimer,
        "independent_signal_count": len(independent_signals),
        "independent_signals": independent_signals,
        "corroborated": len(independent_signals) >= REFUND_MIN_SIGNALS,
        "flag": len(independent_signals) >= 1 or hub_fraudulent,
        "reason": (
            f"{len(independent_signals)} independent signal(s): {independent_signals or 'none'}; "
            f"buyer is a {claimer} claimer (count={claim_count}); "
            f"hub={order.hub_id} cases={hub_case_count} fraudulent={hub_fraudulent}"
        ),
    }

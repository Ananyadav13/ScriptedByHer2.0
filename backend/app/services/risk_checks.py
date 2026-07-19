"""Deterministic risk checks — plain functions, NO LLM.

Each returns a JSON-serializable dict with concrete numbers + a boolean `flag`,
so the agent (and the SSE trace) can cite the exact evidence.

Design rules encoded here:
- A branded listing priced far below MRP is a counterfeit signal.
- A review burst only counts as fake-review evidence when the spike coincides
  with a high share of brand-new accounts — an honest viral seller (real,
  old accounts) must never be flagged.
- Delivery fast-track needs TWO independent signals; serial claimers get routed
  to manual review, not auto-refunded.
"""
from __future__ import annotations

from collections import Counter
from ..time_utils import utcnow

from .rules import (
    BURST_MIN_PEAK,
    BURST_NEW_SHARE,
    HUB_ESCALATE_CASE_COUNT,
    MANUAL_REVIEW_WEIGHT,
    MEDIA_REVIEW_WEIGHT,
    MIN_ORDERS_FOR_ACTION,
    MIN_TRUSTWORTHY_REVIEWS,
    SELLER_QC_SLA_DAYS,
    NEW_ACCOUNT_AGE_DAYS,
    PRICE_BELOW_MRP_RATIO,
    RECENT_REVIEW_WEIGHT,
    RECENT_REVIEW_WINDOW_DAYS,
    REFUND_MIN_SIGNALS,
    REPEAT_CASE_COUNT,
    SELLER_PENALTY_MAX,
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

    new_accounts = sum(1 for r in reviews if r.reviewer_account_age_days < NEW_ACCOUNT_AGE_DAYS)
    new_share = new_accounts / total

    spike = peak_day_count >= BURST_MIN_PEAK
    flag = spike and new_share >= BURST_NEW_SHARE
    return {
        "total_reviews": total,
        "peak_day_count": peak_day_count,
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
    now = utcnow()
    weighted_sum = 0.0
    weight_total = 0.0
    counted = 0
    for r in reviews:
        if r.reviewer_account_age_days < NEW_ACCOUNT_AGE_DAYS:
            continue  # discount fake/new-account cluster entirely
        age_days = (now - r.created_at).days
        w = RECENT_REVIEW_WEIGHT if age_days <= RECENT_REVIEW_WINDOW_DAYS else OLD_REVIEW_WEIGHT
        # human-written reviews outrank AI-derived (image/video) signal
        w *= MANUAL_REVIEW_WEIGHT if getattr(r, "source", "manual") == "manual" else MEDIA_REVIEW_WEIGHT
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
    age_days = (utcnow() - seller.account_created_at).days
    flags = list(seller.trust_flags or [])
    new_account = age_days < 90 or "new_account_cluster" in flags
    repeat_offender = (seller.case_count or 0) >= REPEAT_CASE_COUNT
    effective = seller_effective_rating(seller)["effective_rating"]
    return {
        "seller_id": seller.id,
        "name": seller.name,
        "rating": seller.rating,                 # stored/legacy rating
        "effective_rating": effective,           # fair, data-derived rating
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


def _product_trust(product) -> tuple[float, int] | None:
    """(trustworthy_rating, genuine_review_count) for a product, or None if insufficient."""
    t = trustworthy_rating(product)
    if not t["sufficient"]:
        return None
    return t["trustworthy_rating"], t["trustworthy_review_count"]


def seller_effective_rating(seller) -> dict:
    """Seller rating derived FROM the data — a review-volume-weighted average of the
    trustworthy ratings of the seller's LIVE products. One bad product among many
    barely moves it; that is the fairness the flat penalty lacked."""
    num = den = 0.0
    live = considered = 0
    for p in seller.products:
        if p.status in ("delisted", "suspended"):
            continue  # removed products stop counting
        live += 1
        pt = _product_trust(p)
        if pt is None:
            continue
        rating, n = pt
        num += rating * n
        den += n
        considered += 1
    effective = round(num / den, 2) if den else None
    return {
        "seller_id": seller.id,
        "effective_rating": effective,
        "live_products": live,
        "rated_products": considered,
        "reason": (
            f"volume-weighted over {considered} rated live product(s) "
            f"of {live} -> {effective}"
        ),
    }


def seller_rating_impact(seller, failed_product) -> dict:
    """FAIR penalty when a product is delisted for fraud/quality: proportional to the
    failed product's share of the seller's genuine reviews, capped at SELLER_PENALTY_MAX.

    50 good products + 1 small failure -> ~0 impact; a seller whose one product IS their
    business -> a large hit. (Logistics/delivery faults should pass reason='fault' and
    incur NO integrity penalty.)"""
    failed = _product_trust(failed_product)
    failed_n = failed[1] if failed else 0
    total_n = 0
    for p in seller.products:
        if p.status in ("delisted", "suspended") and p.id != failed_product.id:
            continue
        pt = _product_trust(p)
        if pt is not None:
            total_n += pt[1]
    share = (failed_n / total_n) if total_n else 1.0
    penalty = round(min(SELLER_PENALTY_MAX, SELLER_PENALTY_MAX * share), 3)
    return {
        "seller_id": seller.id,
        "failed_product": failed_product.id,
        "failed_review_share": round(share, 3),
        "penalty": penalty,
        "reason": (
            f"failed product = {share:.1%} of seller's genuine reviews -> "
            f"rating penalty {penalty} (max {SELLER_PENALTY_MAX})"
        ),
    }


def order_volume(order_count: int) -> dict:
    """Confidence floor: a hard lock/ban needs >= MIN_ORDERS_FOR_ACTION orders of
    evidence. Below that, prefer a reversible action (hold / relabel / QC request)
    so we never punish a seller on thin data. Overwhelming authenticity signals
    are still surfaced; this only gates the *hard* outcomes."""
    meets = order_count >= MIN_ORDERS_FOR_ACTION
    return {
        "order_count": order_count,
        "min_for_hard_action": MIN_ORDERS_FOR_ACTION,
        "meets_confidence_floor": meets,
        "reason": (
            f"{order_count} orders >= {MIN_ORDERS_FOR_ACTION} -> enough evidence for a hard action"
            if meets else
            f"only {order_count} orders (< {MIN_ORDERS_FOR_ACTION}) -> prefer a reversible action"
        ),
    }


def qc_sla_status(product) -> dict:
    """Seller quality-check video request + latency SLA (counterfeit flow step 3).

    Once we request a QC video, the seller has SELLER_QC_SLA_DAYS to respond. No
    response past the deadline is non-cooperation -> escalate to a hard lock."""
    requested_at = getattr(product, "qc_requested_at", None)
    responded = bool(getattr(product, "qc_responded", False))
    if requested_at is None:
        return {"qc_requested": False, "qc_responded": False, "qc_overdue": False,
                "reason": "no quality-check video requested"}
    days = (utcnow() - requested_at).days
    overdue = (not responded) and days >= SELLER_QC_SLA_DAYS
    return {
        "qc_requested": True,
        "qc_responded": responded,
        "days_since_request": days,
        "sla_days": SELLER_QC_SLA_DAYS,
        "qc_overdue": overdue,
        "reason": (
            f"QC video responded after {days}d" if responded else
            f"QC video overdue: {days}d >= {SELLER_QC_SLA_DAYS}d SLA -> escalate" if overdue else
            f"QC video pending: {days}d of {SELLER_QC_SLA_DAYS}d SLA"
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

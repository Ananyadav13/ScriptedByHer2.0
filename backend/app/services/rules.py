"""Single source of truth for every tunable threshold in the trust system.

Values chosen for market sensibility (Indian value-marketplace context, where the
guiding principle is: authenticity matters, but NOT at the cost of the buyer or
seller community). Each constant carries the rationale so they can be defended and
tuned. Nothing here imports the LLM — these feed the deterministic services.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Counterfeit / catalog-risk signals
# ---------------------------------------------------------------------------
PRICE_BELOW_MRP_RATIO = 0.35   # a *branded* item priced under 35% of MRP is implausible
NEW_ACCOUNT_AGE_DAYS = 30      # reviewer account younger than this = "new" (industry norm)
BURST_MIN_PEAK = 8             # >= this many reviews in a single day is a spike
BURST_NEW_SHARE = 0.50         # ...AND >= this share from new accounts => coordinated fake burst

# ---------------------------------------------------------------------------
# 2. Trustworthy rating (the ONLY satisfaction measure used for decisions)
#    Recent, established-account reviews reflect real satisfaction; the
#    manipulable cluster (brand-new accounts) is discounted to zero.
# ---------------------------------------------------------------------------
RECENT_REVIEW_WINDOW_DAYS = 90     # reviews within this window are "recent"
RECENT_REVIEW_WEIGHT = 2.0         # recent reviews count double
OLD_REVIEW_WEIGHT = 1.0
MIN_TRUSTWORTHY_REVIEWS = 3        # fewer genuine reviews than this => rating is "insufficient"

# ---------------------------------------------------------------------------
# 3. Decision thresholds (the graduated action ladder)
# ---------------------------------------------------------------------------
BAN_RATING = 2.0                 # trustworthy rating <= this AND repeat cases => ban/suspend
PRODUCT_HOLD_RATING = 3.0        # trustworthy rating < this => hold the listing on BUY NOW
SELLER_CONCERN_RATING = 2.0      # seller rating < this is a serious concern
INCONSISTENCY_EXEMPT_RATING = 3.8  # quality mismatch but rating >= this => notify only, don't hold

# ---------------------------------------------------------------------------
# 4. Repeat-offender frequency (buyer / seller / hub)
#    "Frequent" = a pattern, not a one-off. 3 substantiated cases in 30 days.
# ---------------------------------------------------------------------------
REPEAT_CASE_COUNT = 3
REPEAT_CASE_WINDOW_DAYS = 30

# ---------------------------------------------------------------------------
# 5. Delivery / dispute (OTP corroboration — see PLAN.md OTP section)
# ---------------------------------------------------------------------------
REFUND_MIN_SIGNALS = 2           # independent corroborating signals for a fast-track refund
SERIAL_CLAIM_COUNT = 5           # buyer claim_history count >= this => serial claimer -> manual review
HUB_ESCALATE_CASE_COUNT = 3      # hub cases (per window) before immediate ops escalation

# ---------------------------------------------------------------------------
# 6. Review weighting — human-written reviews outrank AI-derived (image/video)
#    ones when computing a product/seller rating. A person typing a complaint is
#    stronger evidence than an agent's read of a photo.
# ---------------------------------------------------------------------------
MANUAL_REVIEW_WEIGHT = 1.5       # multiplier for human-written reviews
MEDIA_REVIEW_WEIGHT = 1.0        # image/video-derived review signal

# ---------------------------------------------------------------------------
# 7. Agent 2 delisting tiers (Phase 4). "The product no longer works for buyers."
#    Evaluated on RECENT reviews. Each tier: (rating_below, min_review_count).
#    Trips => remove from catalogue, drop seller rating, notify seller (with logs).
# ---------------------------------------------------------------------------
DELIST_TIERS = [
    (3.0, 1000),   # avg recent rating < 3.0 across >= 1000 recent reviews
    (2.0, 700),    # < 2.0 across >= 700
    (1.0, 500),    # <= 1.0 across >= 500  (treated as < 1.01)
]

# ---------------------------------------------------------------------------
# 8. FAIR seller-rating impact (replaces a flat penalty — a flat -0.3 punishes a
#    50-product seller the same as a 1-product scammer, which is unfair).
#    The seller's rating is a REVIEW-VOLUME-WEIGHTED average of their live
#    products, so a delist affects it only in proportion to that product's share
#    of the seller's genuine reviews. An explicit fraud penalty is likewise
#    scaled by that share and capped.
# ---------------------------------------------------------------------------
SELLER_PENALTY_MAX = 0.5             # worst-case hit, only for a seller who is essentially all-fraud
# fault delists (logistics / delivery) do NOT touch the seller integrity score at all

# ---------------------------------------------------------------------------
# 9. Real-time behavioural factors (make decisions feel live, not one-shot).
#    Consumed by Agent 1 tripwires (Phase 4 wiring) and the dispute flow (Phase 3).
# ---------------------------------------------------------------------------
SELLER_COUNTERFEIT_RATING = 2.5      # seller rating <= this + price flag => strong counterfeit lean
PEAK_FAKE_WINDOW_DAYS = 3            # window around a product's rating-peak day to inspect
PEAK_FAKE_SHARE = 0.50              # >= this share of near-peak reviews from new accounts => manipulated peak
RATING_TREND_WINDOW_DAYS = 30        # compare last-30d vs prior-30d trustworthy rating
RATING_DROP_ALERT = 0.5             # a drop >= this across windows => deteriorating product (tripwire)
RETURN_RATE_ALERT = 0.30            # > 30% recent returns/RTO => quality problem
DISPUTE_RATE_ALERT = 0.10           # > 10% of recent orders disputed => investigate
PHOTO_MISMATCH_SHARE = 0.40         # > 40% of review photos contradict the listing (vision, Phase 3)
SELLER_QC_SLA_DAYS = 7              # seller quality-check response deadline before we act
MIN_ORDERS_FOR_ACTION = 20          # confidence floor: need >= this many orders before a hard lock/ban

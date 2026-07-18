"""Single source of truth for every tunable threshold in the trust system.

Values chosen for market sensibility (Indian value-marketplace context, where the
guiding principle is: authenticity matters, but NOT at the cost of the buyer or
seller community). Each constant carries the rationale so they can be defended and
tuned. Nothing here imports the LLM — these feed the deterministic services.

TWO INVARIANTS HOLD, and `tests/test_rules_are_source_of_truth.py` enforces both:

  1. Every constant defined here is CONSUMED somewhere. A threshold nobody reads is
     documentation pretending to be code — it invites a reader (or a judge) to believe
     a rule is enforced when nothing enforces it.
  2. No threshold is restated as a literal in `agents/prompts.py`. The prompts
     INTERPOLATE from this module, so tuning a value here changes the deterministic
     engine and what the agent is told at the same time. Otherwise the two drift and
     the agent argues for outcomes `_execute_action` will refuse to carry out.
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
PRODUCT_HOLD_RATING = 3.0        # trustworthy rating < this => hold the listing
INCONSISTENCY_EXEMPT_RATING = 3.8  # quality mismatch but rating >= this => notify only, don't hold

# ---------------------------------------------------------------------------
# 4. Repeat-offender frequency (buyer / seller / hub)
#    "Frequent" = a pattern, not a one-off: 3 substantiated cases.
#    NOTE: `case_count` on Seller/Buyer/Hub is a running total, not a rolling
#    window — ageing cases out would need a per-case timestamp table, which this
#    build does not have. Documented here so the constant does not imply more
#    precision than the data supports.
# ---------------------------------------------------------------------------
REPEAT_CASE_COUNT = 3

# ---------------------------------------------------------------------------
# 5. Delivery / dispute (OTP corroboration)
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
# 7. Agent 2 delisting tiers. "The product no longer works for buyers."
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
#    Consumed by Agent 1 tripwires and the dispute flow.
# ---------------------------------------------------------------------------
RATING_TREND_WINDOW_DAYS = 30        # compare last-30d vs prior-30d trustworthy rating
RATING_DROP_ALERT = 0.5             # a drop >= this across windows => deteriorating product (tripwire)
RETURN_RATE_ALERT = 0.30            # > 30% recent returns/RTO => quality problem
DISPUTE_RATE_ALERT = 0.10           # > 10% of recent orders disputed => investigate
SELLER_QC_SLA_DAYS = 7              # seller quality-check response deadline before we act
MIN_ORDERS_FOR_ACTION = 20          # confidence floor: need >= this many orders before a hard lock/ban

# ---------------------------------------------------------------------------
# 10. Agent 2 — review clustering + catalog integrity.
#     We act on AGREEMENT (how consistently buyers report the same problem), not
#     raw complaint count — one loud review is noise; a shared complaint is signal.
# ---------------------------------------------------------------------------
CLUSTER_MIN_AGREEMENT = 0.30       # a cluster is "actionable" when >= this share of negative reviews agree
NEGATIVE_REVIEW_MAX_RATING = 2     # reviews rated <= this are "negative" (the clustering input)
MAX_CLUSTER_TEXTS = 60             # cap distinct complaint phrasings sent to the LLM (cost control)
# clusters that a seller can FIX with a corrected listing (vs. suspend / logistics-refer)
FIXABLE_CLUSTERS = ("fabric_mismatch", "size_issue")

# ---------------------------------------------------------------------------
# 11. Mandatory listing fields (catalog gate + new-listing flow).
#     A listing (or a new one) is blocked/held until these are present. The
#     listing VIDEO is mandatory too (it is the canonical media reference — §8).
# ---------------------------------------------------------------------------
MANDATORY_FIELDS = ("size_chart_json", "fabric_claim", "listing_video_path")

# ---------------------------------------------------------------------------
# 12. QUALITY FINGERPRINT — the "golden fields" (variant-invariant attributes).
#
#     A seller films ONE listing video, but sells the same garment in several
#     colourways. Comparing a buyer's dispute video of the BLUE kurti against a
#     listing video of the BLACK one makes colour the loudest "discrepancy" and
#     false-flags an honest seller. The product is the same; only the shade differs.
#
#     So we never compare pixels across variants. The listing video is distilled ONCE
#     into the attributes every colourway physically shares — weave, sheen, texture,
#     opacity, stitch density, drape — and a dispute is judged against THOSE.
#
#     `QUALITY_INVARIANT_ATTRS` is the single source of truth for what may be compared.
#     `VARIANT_SPECIFIC_ATTRS` can differ between variants for entirely innocent reasons
#     and are NEVER counted as evidence of a mismatch — the deterministic diff in
#     services/quality_fingerprint.py drops them regardless of what the model reports,
#     so a vision model cannot cause a colour false-flag even if it tries.
#
#     Exception: a buyer whose actual complaint IS "wrong colour sent" must be heard —
#     colour is compared only when the dispute explicitly claims it (see
#     COLOUR_SENSITIVE_CLAIMS), and even then it is reported separately.
# ---------------------------------------------------------------------------
QUALITY_INVARIANT_ATTRS = (
    "weave_structure",    # knit vs woven; tight vs loose  — a fabric's build
    "surface_sheen",      # matte / semi-matte / glossy    — the cotton-vs-polyester tell
    "fibre_texture",      # fibrous / smooth / plasticky
    "opacity",            # opaque / semi-sheer / sheer
    "stitch_quality",     # seam + hem density and finish
    "drape",              # stiff / structured / fluid
    "embellishment_type", # print / embroidery / sequins / none  (TYPE, not colour)
)
VARIANT_SPECIFIC_ATTRS = ("colour", "shade", "print_colourway")

# A dispute must name one of these for colour to be compared at all.
COLOUR_SENSITIVE_CLAIMS = ("wrong_colour", "wrong_item", "colour_mismatch")

# Share of COMPARED invariant attributes that must diverge before the media read counts
# as a material mismatch. 2 of 7 golden fields disagreeing is noise (lighting, wear);
# a genuine fabric swap moves sheen + texture + weave together.
QUALITY_DIVERGENCE_SHARE = 0.40
# Below this many readable invariant attributes the comparison is too thin to mean anything.
MIN_COMPARABLE_ATTRS = 3

# Numerical Assumptions, Per-Function Usage & Decision Triggers

Every tunable number, **which function consumes it and how**, and the exact rule it drives.

**Source of truth in code:** [`backend/app/services/rules.py`](backend/app/services/rules.py).
Change a value there and the system follows — including the agent prompts, which
**interpolate** these constants rather than restating them. This is enforced, not just
intended: [`tests/test_rules_are_source_of_truth.py`](backend/tests/test_rules_are_source_of_truth.py)
fails the build if a constant goes unused, or if a threshold is hardcoded as a literal in
`prompts.py`.

This document is the human-readable mirror of that file. It describes **only what the code
does today**; nothing here is aspirational.

Guiding principle: *authenticity matters, but **not** at the cost of the buyer or seller
community.* A cheap knockoff people knowingly love ≠ a counterfeit people regret; a seller
with 50 good products and one dud is not a scammer.

---

## 1. Constants (value + rationale)

| Group | Constant | Value | Rationale |
|---|---|---|---|
| **Counterfeit** | `PRICE_BELOW_MRP_RATIO` | `0.35` | branded price < 35% of MRP is implausible |
| | `NEW_ACCOUNT_AGE_DAYS` | `30` | reviewer account younger = "new" |
| | `BURST_MIN_PEAK` | `8` | ≥ 8 reviews in one day = a spike |
| | `BURST_NEW_SHARE` | `0.50` | AND ≥ 50% new accounts ⇒ fake burst |
| **Trustworthy rating** | `RECENT_REVIEW_WINDOW_DAYS` | `90` | reviews within 90 days = "recent" |
| | `RECENT_REVIEW_WEIGHT` / `OLD_REVIEW_WEIGHT` | `2.0` / `1.0` | recent reviews count double |
| | `MANUAL_REVIEW_WEIGHT` / `MEDIA_REVIEW_WEIGHT` | `1.5` / `1.0` | human-written > AI image/video read |
| | `MIN_TRUSTWORTHY_REVIEWS` | `3` | fewer genuine reviews ⇒ "insufficient" |
| **Ladder** | `BAN_RATING` | `2.0` | ≤ 2.0 + repeat cases ⇒ ban |
| | `PRODUCT_HOLD_RATING` | `3.0` | < 3.0 ⇒ hold the listing |
| | `INCONSISTENCY_EXEMPT_RATING` | `3.8` | ≥ 3.8 ⇒ notify only / relabel, don't hold |
| **Repeat offender** | `REPEAT_CASE_COUNT` | `3` | 3 substantiated cases = a pattern |
| **Delivery/dispute** | `REFUND_MIN_SIGNALS` | `2` | ≥ 2 independent signals ⇒ fast-track refund |
| | `SERIAL_CLAIM_COUNT` | `5` | ≥ 5 claims ⇒ serial ⇒ manual review |
| | `HUB_ESCALATE_CASE_COUNT` | `3` | ≥ 3 hub cases ⇒ immediate ops escalation |
| **Real-time factors** | `RATING_TREND_WINDOW_DAYS` | `30` | last-30d vs prior-30d comparison window |
| | `RATING_DROP_ALERT` | `0.5` | trustworthy drop ≥ 0.5 across windows ⇒ tripwire |
| | `RETURN_RATE_ALERT` | `0.30` | > 30% recent returns/RTO ⇒ quality problem |
| | `DISPUTE_RATE_ALERT` | `0.10` | > 10% recent orders disputed ⇒ investigate |
| | `SELLER_QC_SLA_DAYS` | `7` | seller quality-check deadline before we act |
| | `MIN_ORDERS_FOR_ACTION` | `20` | confidence floor before a hard lock/ban |
| **Fair seller rating** | `SELLER_PENALTY_MAX` | `0.5` | max hit, only for an all-fraud seller |
| **Agent-2 delist** | `DELIST_TIERS` | `(3.0,1000)·(2.0,700)·(1.0,500)` | recent trustworthy < R over ≥ N ⇒ delist |
| **Agent-2 cluster** | `CLUSTER_MIN_AGREEMENT` | `0.30` | a cluster is "actionable" at ≥ 30% agreement (not raw count) |
| | `NEGATIVE_REVIEW_MAX_RATING` | `2` | reviews ≤ 2★ are the clustering input |
| | `MAX_CLUSTER_TEXTS` | `60` | cap distinct phrasings sent to the LLM (cost) |
| | `FIXABLE_CLUSTERS` | `fabric_mismatch, size_issue` | clusters a corrected listing can fix |
| **Mandatory fields** | `MANDATORY_FIELDS` | `size_chart_json, fabric_claim, listing_video_path` | gate: video always; size chart for apparel/footwear; fabric for apparel/home |
| **Quality fingerprint** | `QUALITY_INVARIANT_ATTRS` | 7 attrs (below) | the only attributes a media dispute may be judged on |
| | `VARIANT_SPECIFIC_ATTRS` | `colour, shade, print_colourway` | dropped before scoring — never evidence of a mismatch |
| | `QUALITY_DIVERGENCE_SHARE` | `0.40` | ≥ 40% of *compared* invariant attrs diverge ⇒ material mismatch |
| | `MIN_COMPARABLE_ATTRS` | `3` | fewer readable attrs ⇒ "too thin to compare" |
| | `COLOUR_SENSITIVE_CLAIMS` | `wrong_colour, wrong_item, colour_mismatch` | the only claims for which colour is examined, and then separately |

`QUALITY_INVARIANT_ATTRS` = `weave_structure`, `surface_sheen`, `fibre_texture`, `opacity`,
`stitch_quality`, `drape`, `embellishment_type` — the "golden fields": how the garment is
**built**, identical across every colourway.

---

## 2. Per-function usage — which values each function reads, and how

### `price_mrp_risk(product)`
- **Reads:** `PRICE_BELOW_MRP_RATIO` (0.35). **From product:** price, mrp, brand.
- **Rule:** `flag = branded AND price/mrp < 0.35`. Returns the ratio + flag.
- *Seeded examples:* Rolex `599/850000` = `0.0007` → flag. Viral shirt `251/278` = `0.90` → no flag.

### `review_burst_risk(product)`
- **Reads:** `BURST_MIN_PEAK` (8), `BURST_NEW_SHARE` (0.50), `NEW_ACCOUNT_AGE_DAYS` (30).
- **Rule:** `flag = (peak_day_reviews ≥ 8) AND (new_account_share ≥ 0.50)`. **Both** required — a spike from *old* accounts never flags (honest viral).

### `trustworthy_rating(product)` — the only satisfaction measure
- **Reads:** `NEW_ACCOUNT_AGE_DAYS`, `RECENT_REVIEW_WINDOW_DAYS`, `RECENT_REVIEW_WEIGHT`, `OLD_REVIEW_WEIGHT`, `MANUAL_REVIEW_WEIGHT`, `MEDIA_REVIEW_WEIGHT`, `MIN_TRUSTWORTHY_REVIEWS`.
- **Per review:** age < 30d → weight **0** (discard fake cluster); else weight = (2.0 if ≤90d else 1.0) × (1.5 if manual else 1.0).
- **Output:** `Σ(rating×w)/Σ(w)`; if genuine reviews < 3 → `None` ("insufficient — no real satisfaction").

### `seller_profile(seller)`
- **Reads:** `REPEAT_CASE_COUNT` (3); calls `seller_effective_rating`. Account age < 90d = "new" (hardcoded).
- **Output:** stored rating, **effective_rating** (fair), case_count, `repeat_offender = cases ≥ 3`.

### `seller_effective_rating(seller)` — fair, data-derived
- **Reads:** nothing directly (aggregates `trustworthy_rating` of each **live** product, weighted by genuine-review count). Delisted/suspended products stop counting.
- **Why:** one bad product among many barely moves the seller — see §4.

### `seller_rating_impact(seller, failed_product)` — fair penalty
- **Reads:** `SELLER_PENALTY_MAX` (0.5).
- **Rule:** `penalty = min(0.5, 0.5 × failed_share)` where `failed_share = failed_product_reviews / all_seller_genuine_reviews`. Delivery/logistics faults incur **no** penalty.

### `delivery_signals(order, buyer, hub)`
- **Reads:** `REFUND_MIN_SIGNALS` (2), `SERIAL_CLAIM_COUNT` (5), `HUB_ESCALATE_CASE_COUNT` (3).
- **Signals:** OTP scans < items, hub anomaly, no geo-verified photo. `corroborated = signals ≥ 2`. `serial = claim_count ≥ 5`. `hub_fraudulent = hub cases ≥ 3`.

### `order_volume(order_count)` — confidence floor
- **Reads:** `MIN_ORDERS_FOR_ACTION` (20). `meets_confidence_floor = order_count ≥ 20`.
- A hard `counterfeit_lock` requires this OR an overdue QC video; otherwise `_execute_action` downgrades to a reversible `request_qc_video`. (Rolex is seeded with 24 orders, so it still locks.)

### `qc_sla_status(product)` — seller QC-video latency SLA
- **Reads:** `SELLER_QC_SLA_DAYS` (7). `qc_overdue = requested & not responded & days ≥ 7 → escalate`.

### `compare_fingerprints(reference, observed, claim_type)` — PURE, no LLM
- **Reads:** `QUALITY_INVARIANT_ATTRS`, `VARIANT_SPECIFIC_ATTRS`, `QUALITY_DIVERGENCE_SHARE` (0.40), `MIN_COMPARABLE_ATTRS` (3), `COLOUR_SENSITIVE_CLAIMS`.
- **Rule:** compare only the 7 invariant attributes readable on **both** sides; `mismatch = diverged/compared ≥ 0.40`. Below 3 comparable attributes → `comparable: false` ("too thin"), never a mismatch.
- **The safeguard:** variant-specific attributes are dropped *before* any share is computed, so a vision model cannot cause a colour false-flag even if it reports one. Colour is examined only when `claim_type` is colour-sensitive, and is then reported in a separate `colour_note` — never folded into the material verdict.
- *Seeded example (kurti):* 5/7 diverge = `0.71` ≥ 0.40 → mismatch; `colour, shade, print_colourway` ignored; cross-variant Black→Blue.

### `check_media_evidence(product_id, db, order_id?)` — ADVISORY, hybrid
- Reads the buyer's evidence into the golden-field schema, then delegates the verdict to `compare_fingerprints`. The **model reads attributes; the rule engine decides.**
- Returns `compared_attributes`, `diverged_attributes`, `ignored_attributes`, `mismatch`, `confidence`, `variant` context and `colour_note`. Never punishes — the manager decides.

### Agent-1 decision (LLM + `_execute_action`)
- The ladder thresholds `BAN_RATING`, `PRODUCT_HOLD_RATING`, `INCONSISTENCY_EXEMPT_RATING`, `MIN_ORDERS_FOR_ACTION` and `SELLER_QC_SLA_DAYS` are **interpolated into the system prompt from `rules.py`** (`prompts.py` is an f-string). There are no numbers to keep in sync by hand, and a test enforces it.
- `_execute_action` independently re-checks the confidence floor and QC-SLA before any hard lock, so a prompt-level mistake cannot produce a punishment the rules do not permit.

### `predict_size(buyer_id, product_id)` — PURE, no LLM
- **Reads:** nothing from `rules.py`; joins the buyer's `kept_size_history_json` × the `size_drift` row (brand+category). `delta < 0` = runs small → size **up**; `delta > 0` = runs large → size **down**. Numeric and S/M/L ladders, clamped at ends. No history + no drift → `no_history` fallback. *E.g. buyer_normal × StepUp footwear: 8 → 9.*

### `delist_tier(rating, count)` + `evaluate_delisting(product, dominant_label?)` — PURE
- **Reads:** `DELIST_TIERS`, `REPEAT_CASE_COUNT`, `BAN_RATING`, `SELLER_PENALTY_MAX` (via `seller_rating_impact`). Tier = most-severe `(rating_below, min_count)` tripped on the **trustworthy rating** + genuine-review count; the `≤1.0` tier is inclusive. **Routing:** `possible_fraud` / repeat-offender → **suspend** (+ proportional penalty); `damaged_delivery` → **logistics_referral** (NO penalty); fixable/other → **correction_window** (+ fix draft for fixable). Never delists on thin genuine reviews.

### `classify_complaints(product)` — PURE, deterministic keyword classifier
- Buckets negative reviews (≤ `NEGATIVE_REVIEW_MAX_RATING`) into the 5 cluster labels (fraud-first, then damage, material, size). Lets the **whole audit route with zero model calls**; the LLM `cluster_reviews` is the richer layer used only where a tier trips.

### `cluster_reviews(product_id)` / `draft_fix(product, cluster)` — LLM, degrades gracefully
- **Reads:** `CLUSTER_MIN_AGREEMENT` (0.30), `MAX_CLUSTER_TEXTS` (60), `NEGATIVE_REVIEW_MAX_RATING`, `FIXABLE_CLUSTERS`. One batched `response_schema` call each. Agreement is **recomputed deterministically** from real counts, and labels are clamped to the five valid values. `draft_fix` writes a `fix_draft` CatalogAction (before/after); on any model error both **degrade gracefully** (empty clusters / deterministic fallback draft) so `/audit` always completes. *Schema note: no open `dict` in a `response_schema` — the corrected size chart is a `list[SizeRow]`.*

### Tripwires `rating_drop` / `return_rate` / `dispute_rate` — PURE
- **Reads:** `RATING_DROP_ALERT` (0.5) over `RATING_TREND_WINDOW_DAYS` (30), `RETURN_RATE_ALERT` (0.30), `DISPUTE_RATE_ALERT` (0.10). A trip FIRES an Agent-1 `run_investigation` — event-driven, not polling.

### Mandatory-fields gate `check_product` / `check_new_listing` — PURE
- **Reads:** `MANDATORY_FIELDS`. Category-aware: `listing_video_path` always; `size_chart_json` for apparel/footwear; `fabric_claim` for apparel/home. Missing on a live listing → hold; missing on a new listing → block at submission.

---

## 3. Counterfeit decision flow

Not a single check — a sequence. Numbers in **bold** come from `rules.py`.

```
1. HARD SIGNAL?   branded price/mrp < 0.35   OR   a fake-review burst
                  (peak ≥ 8/day AND ≥ 50% new accounts)
                  OR a confirmed media mismatch (≥ 40% of compared golden fields).

2. DO GENUINE BUYERS VOUCH?   trustworthy rating ≥ 3.8
      → YES: do NOT lock. `relabel_required` — the seller must describe it honestly
             as a knockoff/inspired item. The sale continues, and the buyer sees a
             soft tip at add-to-cart.

3. SIGNAL BUT THIN EVIDENCE?  (orders < 20 and no overdue QC video)
      → `request_qc_video`: reversible. The seller has 7 days to prove authenticity.
      → no response past the SLA → qc_overdue → escalate to a lock.

4. LOCK when the authenticity signal is hard, the trustworthy rating is low or
   insufficient, AND the confidence floor is met (orders ≥ 20 OR QC overdue).
   Otherwise prefer relabel / notify / QC-request.

5. CONCLUSION RESTS ON MEDIA?  → `recommend_review`, never a punishment.
   Soft `flagged` status, sale continues, routed to the manager queue.
```

Steps 3–4 are enforced twice: the prompt instructs them, and `_execute_action`
re-validates the floor before applying a lock.

---

## 4. Fair seller-rating model (replaces a flat −0.3)

A flat penalty is unfair: it hits a 50-product seller the same as a 1-product scammer.
Instead, **the seller rating is derived from the data** (volume-weighted average of live
products' trustworthy ratings), and any explicit fraud penalty is **proportional to the
failed product's share** of the seller's genuine reviews, capped at `0.5`.

| Case | Failed share | Penalty (verified) |
|---|---|---|
| 50 solid products (~4.4★), one small dud fails | 2% | **0.01** |
| Seller whose one failing product *is* their business | 98% | **0.49** |

Only **fraud/quality** delists touch the seller integrity score; **delivery/logistics**
faults do not (they are the hub's problem, not the seller's).

---

## 5. Real-time factors (what makes it live, not one-shot)

These feed the **tripwire** triggers — event-driven, not polling:

| Factor | Trigger | Meaning |
|---|---|---|
| Rating trajectory | last-30d trustworthy drops ≥ `0.5` vs prior 30d | product deteriorating → re-investigate |
| Return / RTO rate | > `30%` recent | quality problem → Agent 2 correction |
| Dispute rate | > `10%` recent orders | systemic issue → investigate |
| Media divergence | ≥ `40%` of compared golden fields diverge | material differs from the listing → advisory review |
| Seller QC SLA | response > `7` days | non-cooperation → escalate |
| Confidence floor | orders ≥ `20` before a hard lock/ban | don't punish on thin data |

---

## 6. Decision triggers at a glance

**Agent 1:**
| Decision | Numeric trigger |
|---|---|
| `ban` | trustworthy ≤ `2.0` AND seller cases ≥ `3` |
| `counterfeit_lock` | hard signal AND trustworthy `None`/low AND (orders ≥ `20` OR QC overdue) |
| `request_qc_video` | hard signal BUT below the confidence floor |
| `relabel_required` | hard signal BUT trustworthy ≥ `3.8` |
| `notify_only` | inconsistency BUT trustworthy ≥ `3.8` |
| `hold_pending_fix` | trustworthy < `3.0` |
| `recommend_review` | conclusion rests on the uncertain media comparison |
| `cleared` | spike but new-account share < `0.50` |

**Delivery:** `refund_fast_track` ≥ `2` signals · `standard_process` = `1` signal · `manual_review` claims ≥ `5` · hub escalation cases ≥ `3`.

**Agent-2 delist:** avg < `3.0`/≥`1000`, < `2.0`/≥`700`, ≤ `1.0`/≥`500` → delist + proportional seller penalty.

---

## 7. Verified example values (seeded scenarios)

Re-verified against the current seed:

| Product | Key numbers | Decision |
|---|---|---|
| Counterfeit Rolex | ratio `0.0007`, burst new-share `1.0`, trustworthy `None`, orders `24` | `counterfeit_lock` |
| Honest viral shirt | ratio `0.90`, new-share `0.0`, trustworthy `4.75` | `cleared` |
| Loved knockoff | ratio `0.06`, trustworthy `4.8` (≥ 3.8) | `relabel_required` |
| Low-rated fraud | trustworthy `1.0`, seller cases `5` | `ban` |
| OTP dispute | `3` independent signals, hub cases `6` | `refund_fast_track` + escalation |
| Kurti fabric dispute | 5/7 golden fields diverge (`0.71`), colour ignored, cross-variant Black→Blue | `recommend_review` |

---

## 8. Hybrid media evidence + the variant problem

Buyer review-videos are too scarce to depend on, so evidence is **hybrid** and the agent is
**advisory** on it.

- **Seller listing video** (`Product.listing_video_path`): a short authentic video recorded at
  listing, the **canonical reference**. Required by the mandatory-fields gate.
- **The variant problem.** A seller films ONE colourway but sells several. Comparing a buyer's
  blue kurti against a black listing video makes colour the loudest "discrepancy" and
  false-flags an honest seller. So the video is distilled **once** into the variant-invariant
  golden fields (`Product.quality_fingerprint_json`), and every dispute — on any colourway —
  is judged against those.
- **Buyer evidence** (`Order.buyer_evidence_json`): photo OR video supplied on a complaint,
  read into the same attribute schema.
- **The verdict is computed, not asked.** `services/quality_fingerprint.py` performs the diff
  with no LLM involvement, using `QUALITY_DIVERGENCE_SHARE` (0.40) over the compared invariant
  attributes. Colour is excluded by construction.
- **Advisory, not binding.** Media is uncertain (lighting, wear, the item may not even be the
  delivered one), so Agent 1 returns **`recommend_review`** with `recommended_action` +
  `suggested_remedy` and routes to the **manager queue** as a soft **`flagged`** status —
  *the sale continues, no buyer impact.* Only deterministic hard signals take an interim
  protective lock, which the manager still confirms. Agents recommend; managers decide.
- **Statuses:** `flagged` (advisory, non-restrictive) vs the restrictive
  `locked` / `on_hold` / `needs_info` / `suspended`.

> **Demo note — pre-extracted fingerprints.** In the seeded demo the kurti's listing
> fingerprint and the buyer's observed attributes are **pre-extracted** into `seed.py`, so the
> comparison is byte-identical on every run and costs zero Gemini quota. The extraction code
> path (`vision.extract_quality_fingerprint` → OpenCV keyframes → one multimodal read) is
> fully implemented and runs live when a real video is present at
> `backend/media/videos/` and the cached fingerprint is cleared — but **no video ships with
> this repository**, so the demo as distributed exercises the deterministic diff, not the
> extraction. See the README's *Media pipeline* section.

*Storage (production concern, not in the demo DB): object store + keyframes/embeddings as the
working set, archive/discard raw video, LLM only on tripwire.*

---

*Tuning note: these are market-sensible defaults, not empirical fits — in production each
threshold is calibrated against labelled outcomes. All live in `rules.py`; tuning is a
one-line change with no logic edits, and the prompts follow automatically.*

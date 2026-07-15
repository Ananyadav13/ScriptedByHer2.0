# Numerical Assumptions, Per-Function Usage & Decision Triggers

Every tunable number, **which function consumes it and how**, and the exact rule it drives.
**Source of truth in code:** [`backend/app/services/rules.py`](backend/app/services/rules.py) —
change a value there and the system follows; this doc is the human-readable mirror.

Guiding principle: *authenticity matters, but **not** at the cost of the buyer or seller
community.* A cheap knockoff people knowingly love ≠ a counterfeit people regret; a seller
with 50 good products and one dud is not a scammer.

> Legend: ✅ built & verified (Phase 2) · 🎥 needs vision (Phase 3) · 🧹 Agent-2 engine (Phase 4)

---

## 1. Constants (value + rationale)

| Group | Constant | Value | Rationale |
|---|---|---|---|
| **Counterfeit** | `PRICE_BELOW_MRP_RATIO` | `0.35` | branded price < 35% of MRP is implausible |
| | `SELLER_COUNTERFEIT_RATING` | `2.5` | seller ≤ 2.5 + price flag ⇒ strong counterfeit lean |
| | `NEW_ACCOUNT_AGE_DAYS` | `30` | reviewer account younger = "new" |
| | `BURST_MIN_PEAK` | `8` | ≥ 8 reviews in one day = a spike |
| | `BURST_NEW_SHARE` | `0.50` | AND ≥ 50% new accounts ⇒ fake burst |
| | `PEAK_FAKE_WINDOW_DAYS` | `3` | window around the rating-peak day to inspect |
| | `PEAK_FAKE_SHARE` | `0.50` | ≥ 50% of near-peak reviews new ⇒ manipulated peak |
| **Trustworthy rating** | `RECENT_REVIEW_WINDOW_DAYS` | `90` | reviews within 90 days = "recent" |
| | `RECENT_REVIEW_WEIGHT` / `OLD_REVIEW_WEIGHT` | `2.0` / `1.0` | recent reviews count double |
| | `MANUAL_REVIEW_WEIGHT` / `MEDIA_REVIEW_WEIGHT` | `1.5` / `1.0` | human-written > AI image/video read |
| | `MIN_TRUSTWORTHY_REVIEWS` | `3` | fewer genuine reviews ⇒ "insufficient" |
| **Ladder** | `BAN_RATING` | `2.0` | ≤ 2.0 + repeat cases ⇒ ban |
| | `PRODUCT_HOLD_RATING` | `3.0` | < 3.0 ⇒ hold on BUY NOW |
| | `SELLER_CONCERN_RATING` | `2.0` | seller < 2.0 = serious concern |
| | `INCONSISTENCY_EXEMPT_RATING` | `3.8` | ≥ 3.8 ⇒ notify only, don't hold |
| **Repeat offender** | `REPEAT_CASE_COUNT` / `REPEAT_CASE_WINDOW_DAYS` | `3` / `30` | 3 substantiated cases in 30 days = a pattern |
| **Delivery/dispute** | `REFUND_MIN_SIGNALS` | `2` | ≥ 2 independent signals ⇒ fast-track refund |
| | `SERIAL_CLAIM_COUNT` | `5` | ≥ 5 claims ⇒ serial ⇒ manual review |
| | `HUB_ESCALATE_CASE_COUNT` | `3` | ≥ 3 hub cases ⇒ immediate ops escalation |
| **Real-time factors** | `RATING_TREND_WINDOW_DAYS` | `30` | last-30d vs prior-30d comparison window |
| | `RATING_DROP_ALERT` | `0.5` | trustworthy drop ≥ 0.5 across windows ⇒ tripwire |
| | `RETURN_RATE_ALERT` | `0.30` | > 30% recent returns/RTO ⇒ quality problem |
| | `DISPUTE_RATE_ALERT` | `0.10` | > 10% recent orders disputed ⇒ investigate |
| | `PHOTO_MISMATCH_SHARE` | `0.40` | > 40% review photos contradict listing 🎥 |
| | `SELLER_QC_SLA_DAYS` | `7` | seller quality-check deadline before we act |
| | `MIN_ORDERS_FOR_ACTION` | `20` | confidence floor before a hard lock/ban |
| **Fair seller rating** | `SELLER_PENALTY_MAX` | `0.5` | max hit, only for an all-fraud seller |
| **Agent-2 delist** | `DELIST_TIERS` | `(3.0,1000)·(2.0,700)·(1.0,500)` | recent avg < R over ≥ N ⇒ delist 🧹 |

---

## 2. Per-function usage — which values each function reads, and how

### `price_mrp_risk(product)` ✅
- **Reads:** `PRICE_BELOW_MRP_RATIO` (0.35). **From product:** price, mrp, brand.
- **Rule:** `flag = branded AND price/mrp < 0.35`. Returns the ratio + flag.
- *Example:* Rolex 599/850000 = `0.0007` → flag. Viral tee 499/999 = `0.50` → no flag.

### `review_burst_risk(product)` ✅
- **Reads:** `BURST_MIN_PEAK` (8), `BURST_NEW_SHARE` (0.50), `NEW_ACCOUNT_AGE_DAYS` (30).
- **Rule:** `flag = (peak_day_reviews ≥ 8) AND (new_account_share ≥ 0.50)`. **Both** required — a spike from *old* accounts never flags (honest viral).

### `trustworthy_rating(product)` ✅ — the only satisfaction measure
- **Reads:** `NEW_ACCOUNT_AGE_DAYS`, `RECENT_REVIEW_WINDOW_DAYS`, `RECENT_REVIEW_WEIGHT`, `OLD_REVIEW_WEIGHT`, `MANUAL_REVIEW_WEIGHT`, `MEDIA_REVIEW_WEIGHT`, `MIN_TRUSTWORTHY_REVIEWS`.
- **Per review:** age < 30d → weight **0** (discard fake cluster); else weight = (2.0 if ≤90d else 1.0) × (1.5 if manual else 1.0).
- **Output:** `Σ(rating×w)/Σ(w)`; if genuine reviews < 3 → `None` ("insufficient — no real satisfaction").

### `seller_profile(seller)` ✅
- **Reads:** `REPEAT_CASE_COUNT` (3); calls `seller_effective_rating`. Account age < 90d = "new" (hardcoded).
- **Output:** legacy rating, **effective_rating** (fair), case_count, `repeat_offender = cases ≥ 3`.

### `seller_effective_rating(seller)` ✅ — fair, data-derived
- **Reads:** nothing directly (aggregates `trustworthy_rating` of each **live** product, weighted by genuine-review count). Delisted/suspended products stop counting.
- **Why:** one bad product among many barely moves the seller — see §4.

### `seller_rating_impact(seller, failed_product)` ✅ — fair penalty
- **Reads:** `SELLER_PENALTY_MAX` (0.5).
- **Rule:** `penalty = min(0.5, 0.5 × failed_share)` where `failed_share = failed_product_reviews / all_seller_genuine_reviews`. Delivery/logistics faults pass `reason='fault'` → **no** penalty.

### `delivery_signals(order, buyer, hub)` ✅
- **Reads:** `REFUND_MIN_SIGNALS` (2), `SERIAL_CLAIM_COUNT` (5), `HUB_ESCALATE_CASE_COUNT` (3).
- **Signals:** OTP scans < items, hub anomaly, no geo-verified photo. `corroborated = signals ≥ 2`. `serial = claim_count ≥ 5`. `hub_fraudulent = hub cases ≥ 3`.

### `image_match_risk(product)` — official-image perceptual hash (still a stub; Phase 3 built the *video* path instead)

### `order_volume(order_count)` ✅ (Phase 3) — confidence floor
- **Reads:** `MIN_ORDERS_FOR_ACTION` (20). `meets_confidence_floor = order_count ≥ 20`.
- A hard `counterfeit_lock` requires this OR an overdue QC video; otherwise `_execute_action`
  downgrades to a reversible `request_qc_video`. (Rolex is seeded 24 orders so it still locks.)

### `qc_sla_status(product)` ✅ (Phase 3) — seller QC-video latency SLA
- **Reads:** `SELLER_QC_SLA_DAYS` (7). `qc_overdue = requested & not responded & days ≥ 7 → escalate`.

### `analyze_video_reviews(product_id)` 🎥 (Phase 3, tool `check_video_reviews`)
- Isolated multimodal sub-call over review-video keyframes. Reads `PHOTO_MISMATCH_SHARE` (0.40):
  `mismatch_flag = observed-material contradicts the fabric_claim in ≥ 40% of frames`. Returns
  observations only (no verdict); raw frames never enter the orchestrator context.

### Agent-1 decision (LLM + `_execute_action`) ✅
- The ladder thresholds `BAN_RATING`, `PRODUCT_HOLD_RATING`, `INCONSISTENCY_EXEMPT_RATING`, `SELLER_CONCERN_RATING` are enforced by the system prompt, which **mirrors these constants** (see `prompts.py`). *Keep the prompt numbers in sync with `rules.py`.*

---

## 3. Counterfeit decision flow — the richer, multi-factor version

Not a single check — a sequence. Numbers in **bold**.

```
1. HARD LEAN?  seller effective rating ≤ 2.5  AND  price/mrp ≤ 0.35
   (a review burst is NOT required here; but a fake-rating cluster around the
    product's rating-PEAK — ≥ 50% new accounts within ±3 days of the peak —
    strengthens it.)  Also weigh video + manual reviews (manual ×1.5).

2. ARE GENUINE BUYERS SATISFIED?  trustworthy rating ≥ 3.8
      → YES: do NOT lock. Send a WARNING to change the name/description
             (relabel as knockoff) to the seller AND their business manager.
             Optionally show the buyer a soft tip at add-to-cart.

3. STILL SUSPECT & rating not clearly good?  Request a seller QUALITY-CHECK video.
      → seller latency > 7 days (no response)                → escalate / lock
      → product sent ≠ user narratives / review photos       → escalate / lock

4. LOCK only when product AND seller ratings are BOTH against the product's
   existence — i.e. trustworthy < 3.0 (regret) and seller ≤ 2.5 — and order
   volume ≥ 20 (confidence floor). Otherwise prefer relabel / notify.
```

Built: steps 1–2 + relabel/notify (Phase 2). **Phase 3 added:** the confidence floor
(`order_volume` — a hard lock needs ≥ `MIN_ORDERS_FOR_ACTION` orders OR an overdue QC video,
else it downgrades to `request_qc_video`), the seller **QC-video request + `SELLER_QC_SLA_DAYS`
latency** (`qc_sla_status`; overdue → escalate), and the **photo-vs-review** consistency via the
vision sub-call (`check_video_reviews` → `mismatch_share` vs `PHOTO_MISMATCH_SHARE`). The vision
tool needs real review-video assets wired into `seed.py` to fire live.

---

## 4. Fair seller-rating model (replaces the flat −0.3)

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

## 5. Real-time factors (what makes it live, not one-shot) — Phase 3/4 wiring

These feed the **tripwire** triggers (see PLAN §5A: event-driven, not polling):

| Factor | Trigger | Meaning |
|---|---|---|
| Rating trajectory | last-30d trustworthy drops ≥ `0.5` vs prior 30d | product deteriorating → re-investigate |
| Return / RTO rate | > `30%` recent | quality problem → Agent 2 correction |
| Dispute rate | > `10%` recent orders | systemic issue → investigate |
| Manipulated peak | ≥ `50%` new accounts within ±`3` days of rating peak | fake-rating burst timed to a peak |
| Photo mismatch 🎥 | > `40%` review photos contradict listing | description fraud |
| Seller QC SLA | response > `7` days | non-cooperation → escalate |
| Confidence floor | orders ≥ `20` before a hard lock/ban | don't punish on thin data |

---

## 6. Decision triggers at a glance

**Agent 1 (first match wins):**
| Decision | Numeric trigger |
|---|---|
| `ban` | trustworthy ≤ `2.0` AND seller cases ≥ `3` |
| `counterfeit_lock` | hard signal AND trustworthy `None`/low AND orders ≥ `20` |
| `relabel_required` | hard signal BUT trustworthy ≥ `3.8` |
| `notify_only` | inconsistency BUT trustworthy ≥ `3.8` |
| `hold_pending_fix` | trustworthy < `3.0` |
| `cleared` | spike but new-account share < `0.50` |

**Delivery:** `refund_fast_track` ≥ `2` signals · `standard_process` = `1` signal · `manual_review` claims ≥ `5` · hub escalation cases ≥ `3`.

**Agent-2 delist:** avg < `3.0`/≥`1000`, < `2.0`/≥`700`, ≤ `1.0`/≥`500` → delist + proportional seller penalty.

---

## 7. Verified example values (seeded scenarios)

| Product | Key numbers | Decision |
|---|---|---|
| Counterfeit Rolex | ratio `0.0007`, peak new-share `1.0`, trustworthy `None` | `counterfeit_lock` |
| Honest viral tee | new-share `0.0`, trustworthy `5.0` | `cleared` |
| Loved knockoff | ratio `0.06`, trustworthy `4.8` (≥ 3.8) | `relabel_required` |
| Low-rated fraud | trustworthy `1.0`, seller cases `5` | `ban` |
| OTP dispute | `3` signals, hub cases `6` | `refund_fast_track` + escalation |

---

*Tuning note: these are market-sensible defaults, not empirical fits — in production each
threshold is calibrated against labelled outcomes. All live in `rules.py`; tuning is a
one-line change with no logic edits.*

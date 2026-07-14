# Numerical Assumptions & Decision Triggers

Every tunable number in the trust system, its rationale, and the exact numeric
rule it drives. **Source of truth in code:** [`backend/app/services/rules.py`](backend/app/services/rules.py)
— change a value there and the whole system follows; this doc is the human-readable mirror.

Guiding principle behind the numbers: *authenticity matters, but **not** at the cost of
the buyer or seller community* (an Indian value-marketplace context — a cheap knockoff
people knowingly love is not the same as a counterfeit people regret).

---

## 1. Constants (values + why)

| Group | Constant | Value | Rationale |
|---|---|---|---|
| **Counterfeit / catalog** | `PRICE_BELOW_MRP_RATIO` | `0.35` | a *branded* item priced under 35% of MRP is implausible |
| | `NEW_ACCOUNT_AGE_DAYS` | `30` | reviewer account younger than this = "new" (industry norm) |
| | `BURST_MIN_PEAK` | `8` | ≥ 8 reviews in a single day is a spike |
| | `BURST_NEW_SHARE` | `0.50` | …AND ≥ 50% from new accounts ⇒ coordinated fake burst |
| **Trustworthy rating** | `RECENT_REVIEW_WINDOW_DAYS` | `90` | reviews within 90 days count as "recent" |
| | `RECENT_REVIEW_WEIGHT` | `2.0` | recent reviews count double |
| | `OLD_REVIEW_WEIGHT` | `1.0` | older reviews baseline |
| | `MIN_TRUSTWORTHY_REVIEWS` | `3` | fewer genuine reviews ⇒ rating is "insufficient" |
| **Ladder thresholds** | `BAN_RATING` | `2.0` | trustworthy ≤ 2.0 AND repeat cases ⇒ ban |
| | `PRODUCT_HOLD_RATING` | `3.0` | trustworthy < 3.0 ⇒ hold on BUY NOW |
| | `SELLER_CONCERN_RATING` | `2.0` | seller rating < 2.0 is a serious concern |
| | `INCONSISTENCY_EXEMPT_RATING` | `3.8` | inconsistency but rating ≥ 3.8 ⇒ notify only, don't hold |
| **Repeat offender** | `REPEAT_CASE_COUNT` | `3` | a pattern, not a one-off |
| | `REPEAT_CASE_WINDOW_DAYS` | `30` | …3 substantiated cases within 30 days |
| **Delivery / dispute** | `REFUND_MIN_SIGNALS` | `2` | independent corroborating signals for a fast-track refund |
| | `SERIAL_CLAIM_COUNT` | `5` | buyer claim count ≥ 5 ⇒ serial claimer ⇒ manual review |
| | `HUB_ESCALATE_CASE_COUNT` | `3` | hub cases (per window) before immediate ops escalation |
| **Review weighting** | `MANUAL_REVIEW_WEIGHT` | `1.5` | human-written reviews outrank AI-derived signal |
| | `MEDIA_REVIEW_WEIGHT` | `1.0` | image/video-derived review signal |
| **Agent-2 delisting** | `DELIST_TIERS` | `(3.0,1000) · (2.0,700) · (1.0,500)` | recent avg rating < R over ≥ N reviews ⇒ delist |
| | `SELLER_RATING_DROP_ON_DELIST` | `0.3` | seller rating penalty on a quality delist |

---

## 2. Trustworthy rating — the only satisfaction measure

```
for each review of a product:
    if reviewer_account_age_days < 30:      weight = 0     # discard fake/new-account cluster
    else:
        weight = 2.0 if age_days <= 90 else 1.0            # recency
        weight *= 1.5 if source == "manual" else 1.0       # human-written > AI image/video read

trustworthy_rating = Σ(rating × weight) / Σ(weight)
if genuine_reviews < 3:  rating = None                     # "insufficient — no real satisfaction signal"
```

Fake 5-star bursts can't buy a good score (new accounts → weight 0); genuine buyers of a
cheap knockoff still can.

---

## 3. Agent 1 — decision ladder (numeric triggers, first match wins)

A "hard authenticity signal" = price ratio < `0.35` **OR** a fake burst **OR** an image mismatch.
A "fake burst" = peak-day reviews ≥ `8` **AND** new-account share ≥ `0.50` (both required).

| Decision | Numeric trigger | Effect |
|---|---|---|
| `ban` | trustworthy ≤ `2.0` **AND** seller cases ≥ `3` | seller suspended |
| `counterfeit_lock` | hard signal **AND** trustworthy `None`/low | listing locked |
| `relabel_required` | hard signal **BUT** trustworthy ≥ `3.8` | stays live; seller relabels as knockoff |
| `notify_only` | quality inconsistency **BUT** trustworthy ≥ `3.8` | sale continues + buyer tip |
| `hold_pending_fix` | trustworthy < `3.0` | listing on hold |
| `cleared` | volume spike but new-account share < `0.50` | none (honest viral) |

---

## 4. Delivery / dispute — numeric triggers

Independent signals = { OTP scans < items, hub anomaly, no geo-verified photo }.

| Decision | Numeric trigger |
|---|---|
| `refund_fast_track` | independent signals ≥ `2` |
| `standard_process` | exactly `1` independent signal |
| `manual_review` | buyer claim count ≥ `5` (serial claimer) |
| hub ops-escalation (immediate) | hub case count ≥ `3` |

---

## 5. Agent-2 delisting tiers (Phase 4 — numbers locked, engine pending)

Evaluated on **recent** reviews; any tier trips ⇒ delist + seller rating − `0.3` + notify seller (logged).

| Tier | Condition |
|---|---|
| 1 | avg rating < `3.0` over ≥ `1000` recent reviews |
| 2 | avg rating < `2.0` over ≥ `700` |
| 3 | avg rating ≤ `1.0` over ≥ `500` |

---

## 6. Verified example values (seeded scenarios)

| Product | Key numbers | Decision |
|---|---|---|
| Counterfeit Rolex | ratio `0.0007`, burst new-share `1.0`, trustworthy `None` | `counterfeit_lock` |
| Honest viral tee | ratio `0.50`, new-share `0.0`, trustworthy `5.0` | `cleared` |
| Loved knockoff | ratio `0.06` (flag), trustworthy `4.8` (≥ 3.8) | `relabel_required` |
| Low-rated fraud | trustworthy `1.0` (≤ 2.0), seller cases `5` (≥ 3) | `ban` |
| OTP dispute | `3` independent signals (≥ 2), hub cases `6` (≥ 3) | `refund_fast_track` + escalation |

---

*Tuning note: these are market-sensible defaults, not empirical fits. In production each
threshold would be calibrated against labelled outcomes; all live in `rules.py` so tuning is
a one-line change with no logic edits.*

"""Deterministic risk-check tests — the trust core (PHASES.md Phase 4, task 7)."""
from __future__ import annotations

from app.services import risk_checks
from app.services.rules import SELLER_PENALTY_MAX

from .conftest import make_order, make_product, make_review, make_seller


# ---- price vs MRP ----
def test_branded_far_below_mrp_flags():
    p = make_product(brand="Rolex", price=599, mrp=850000)
    r = risk_checks.price_mrp_risk(p)
    assert r["flag"] is True
    assert r["price_to_mrp_ratio"] < 0.35


def test_fair_price_does_not_flag():
    p = make_product(brand="TrendyThreads", price=499, mrp=999)
    assert risk_checks.price_mrp_risk(p)["flag"] is False


# ---- review burst: the honest-viral non-flag case (the deck promise) ----
def test_review_burst_flags_new_account_spike():
    reviews = [make_review(age_days=2, created_days_ago=2) for _ in range(12)]
    r = risk_checks.review_burst_risk(make_product(reviews=reviews))
    assert r["flag"] is True
    assert r["new_account_share"] >= 0.5


def test_honest_viral_spike_from_old_accounts_never_flags():
    # 15 reviews the SAME day (a spike) but all from established accounts -> must NOT flag.
    reviews = [make_review(age_days=400 + i * 20, created_days_ago=3) for i in range(15)]
    r = risk_checks.review_burst_risk(make_product(reviews=reviews))
    assert r["peak_day_count"] >= 8          # it IS a spike
    assert r["new_account_share"] == 0.0
    assert r["flag"] is False                # ...but organic -> not flagged


# ---- trustworthy rating: discounts the fake new-account cluster ----
def test_trustworthy_rating_discounts_new_accounts():
    # 12 fake 5★ from 2-day accounts + 3 genuine 2★ from old accounts.
    fakes = [make_review(rating=5, age_days=2, created_days_ago=2) for _ in range(12)]
    genuine = [make_review(rating=2, age_days=300, created_days_ago=10) for _ in range(3)]
    r = risk_checks.trustworthy_rating(make_product(reviews=fakes + genuine))
    assert r["sufficient"] is True
    assert r["trustworthy_review_count"] == 3      # fakes discarded
    assert r["trustworthy_rating"] == 2.0          # only genuine reviews count


def test_trustworthy_rating_insufficient_when_all_new():
    fakes = [make_review(rating=5, age_days=2) for _ in range(12)]
    r = risk_checks.trustworthy_rating(make_product(reviews=fakes))
    assert r["sufficient"] is False
    assert r["trustworthy_rating"] is None


def test_manual_reviews_outweigh_media_reviews():
    # equal counts, opposite ratings: manual 4★ (w1.5) vs media 2★ (w1.0) -> skews above 3.
    reviews = ([make_review(rating=4, source="manual", age_days=300) for _ in range(3)]
               + [make_review(rating=2, source="video", age_days=300) for _ in range(3)])
    r = risk_checks.trustworthy_rating(make_product(reviews=reviews))
    assert r["trustworthy_rating"] > 3.0


# ---- seller rating impact: FAIRNESS (proportional, not flat) ----
def _rated_product(pid, rating, n, status="active"):
    return make_product(pid=pid, reviews=[make_review(rating=rating, age_days=300) for _ in range(n)],
                        status=status)


def test_seller_penalty_tiny_for_one_dud_among_many():
    good = [_rated_product(f"g{i}", 5, 100) for i in range(50)]   # 5000 genuine reviews
    dud = _rated_product("dud", 1, 100)                           # 100 reviews (~2%)
    seller = make_seller(products=good + [dud])
    imp = risk_checks.seller_rating_impact(seller, dud)
    assert imp["penalty"] < 0.05                                  # barely moves a big seller


def test_seller_penalty_maxes_for_single_product_scammer():
    only = _rated_product("only", 1, 100)
    seller = make_seller(products=[only])
    imp = risk_checks.seller_rating_impact(seller, only)
    assert imp["penalty"] == SELLER_PENALTY_MAX                   # their one product IS the business


def test_seller_effective_rating_volume_weighted():
    big = _rated_product("big", 5, 900)
    small = _rated_product("small", 1, 100)
    seller = make_seller(products=[big, small])
    eff = risk_checks.seller_effective_rating(seller)["effective_rating"]
    assert 4.5 < eff <= 4.7                                       # dominated by the 900-review product


# ---- delivery signals ----
def test_two_signals_corroborate_refund():
    order = make_order(otp=1, items=3, hub_anomaly=True, geo=False)   # otp mismatch + hub + no geo = 3
    buyer = make_seller()  # reuse as a namespace with claim_history
    buyer.claim_history = {"count": 0}
    r = risk_checks.delivery_signals(order, buyer, hub=make_seller(case_count=6))
    assert r["independent_signal_count"] >= 2
    assert r["corroborated"] is True
    assert r["hub_fraudulent"] is True


def test_serial_claimer_flagged_not_corroboration():
    order = make_order(otp=1, items=1, hub_anomaly=False, geo=True)   # zero independent signals
    buyer = make_seller(); buyer.claim_history = {"count": 7}
    r = risk_checks.delivery_signals(order, buyer, hub=make_seller(case_count=0))
    assert r["claimer_classification"] == "serial"
    assert r["corroborated"] is False


# ---- confidence floor ----
def test_order_volume_confidence_floor():
    assert risk_checks.order_volume(24)["meets_confidence_floor"] is True
    assert risk_checks.order_volume(5)["meets_confidence_floor"] is False

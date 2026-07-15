"""Delisting-engine tests: tier boundaries + fair routing (Phase 4, task 7).

`delist_tier` and `evaluate_delisting` are PURE (no LLM, no DB)."""
from __future__ import annotations

from app.services import delisting
from app.services.rules import SELLER_PENALTY_MAX

from .conftest import make_product, make_review, make_seller


# ---- DELIST_TIERS boundary math ----
def test_tier0_boundary_needs_rating_below_3_and_1000():
    assert delisting.delist_tier(2.99, 1000) == 0
    assert delisting.delist_tier(3.0, 1000) is None    # 3.0 is not < 3.0
    assert delisting.delist_tier(2.99, 999) is None     # one review short


def test_tier1_boundary():
    assert delisting.delist_tier(1.99, 700) == 1
    assert delisting.delist_tier(1.99, 699) is None


def test_tier2_boundary_is_inclusive_of_one_star():
    assert delisting.delist_tier(1.0, 500) == 2         # <= 1.0 inclusive
    assert delisting.delist_tier(1.01, 500) is None
    assert delisting.delist_tier(1.0, 499) is None


def test_most_severe_tier_wins():
    assert delisting.delist_tier(1.0, 1000) == 2        # all three trip -> worst
    assert delisting.delist_tier(2.5, 1200) == 0


def test_no_rating_no_tier():
    assert delisting.delist_tier(None, 5000) is None


# ---- deterministic complaint classifier ----
def _neg(text, n):
    return [make_review(rating=1, age_days=300, text=text) for _ in range(n)]


def test_classify_fraud():
    p = make_product(reviews=_neg("Fake product, counterfeit scam", 10))
    assert delisting.classify_complaints(p)["dominant"] == "possible_fraud"


def test_classify_damaged():
    p = make_product(reviews=_neg("Arrived broken, damaged in transit", 10))
    assert delisting.classify_complaints(p)["dominant"] == "damaged_delivery"


def test_classify_size():
    p = make_product(reviews=_neg("No size chart, runs small, wrong size", 10))
    assert delisting.classify_complaints(p)["dominant"] == "size_issue"


# ---- full routing ----
def _product_that_trips(text, n=1000, rating=1):
    reviews = [make_review(rating=rating, age_days=300, text=text) for _ in range(n)]
    p = make_product(pid="pf", reviews=reviews)
    seller = make_seller(sid="sf", products=[p])
    p.seller = seller
    return p, seller


def test_fraud_cluster_suspends_with_penalty():
    p, seller = _product_that_trips("Fake counterfeit scam product", rating=1)
    ev = delisting.evaluate_delisting(p)
    assert ev["action"] == "suspend"
    assert ev["seller_penalty"]["penalty"] == SELLER_PENALTY_MAX  # single-product seller


def test_damaged_cluster_refers_to_logistics_with_no_penalty():
    p, seller = _product_that_trips("Arrived broken, shattered in transit", rating=1)
    ev = delisting.evaluate_delisting(p)
    assert ev["action"] == "logistics_referral"
    assert ev["seller_penalty"] is None                          # fault -> no seller impact


def test_size_cluster_correction_window_and_fixable():
    p, seller = _product_that_trips("No size chart, wrong size", rating=2, n=1000)
    ev = delisting.evaluate_delisting(p)
    assert ev["action"] == "correction_window"
    assert ev["fixable"] is True
    assert ev["seller_penalty"]["penalty"] > 0


def test_repeat_offender_seller_forces_suspend():
    # dominant complaint is generic 'other', but a repeat-offender seller -> suspend anyway.
    reviews = [make_review(rating=1, age_days=300, text="meh whatever") for _ in range(1000)]
    p = make_product(pid="po", reviews=reviews)
    seller = make_seller(sid="so", products=[p], case_count=5)
    p.seller = seller
    ev = delisting.evaluate_delisting(p)
    assert ev["action"] == "suspend"


def test_healthy_product_is_kept():
    reviews = [make_review(rating=5, age_days=300, text="love it") for _ in range(1000)]
    p = make_product(pid="ph", reviews=reviews)
    p.seller = make_seller(products=[p])
    ev = delisting.evaluate_delisting(p)
    assert ev["delist"] is False
    assert ev["action"] == "keep"


def test_thin_evidence_not_delisted():
    # only 2 genuine reviews -> trustworthy insufficient -> never delist on thin data.
    reviews = [make_review(rating=1, age_days=300, text="fake scam") for _ in range(2)]
    p = make_product(pid="pt", reviews=reviews)
    p.seller = make_seller(products=[p])
    assert delisting.evaluate_delisting(p)["delist"] is False

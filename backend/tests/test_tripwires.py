"""Deterministic tripwire tests (Phase 4, task 7). No LLM."""
from __future__ import annotations

from app.models import Order
from app.services import tripwires

from .conftest import make_order, make_product, make_review


def test_rating_drop_trips_on_deterioration():
    prior = [make_review(rating=5, age_days=300, created_days_ago=45) for _ in range(10)]
    recent = [make_review(rating=2, age_days=300, created_days_ago=10) for _ in range(10)]
    r = tripwires.rating_drop(make_product(reviews=prior + recent))
    assert r["tripped"] is True
    assert r["drop"] >= 0.5


def test_rating_stable_does_not_trip():
    prior = [make_review(rating=4, age_days=300, created_days_ago=45) for _ in range(10)]
    recent = [make_review(rating=4, age_days=300, created_days_ago=10) for _ in range(10)]
    assert tripwires.rating_drop(make_product(reviews=prior + recent))["tripped"] is False


class _FakeQuery:
    def __init__(self, rows): self._rows = rows
    def filter(self, *a, **k): return self
    def all(self): return self._rows


class _FakeDB:
    def __init__(self, orders): self._orders = orders
    def query(self, model): return _FakeQuery(self._orders)


def test_return_rate_trips_above_threshold():
    orders = [make_order(status="refunded") for _ in range(4)] + [make_order() for _ in range(6)]
    r = tripwires.return_rate(make_product(), _FakeDB(orders))   # 40% > 30%
    assert r["tripped"] is True
    assert r["rate"] == 0.4


def test_dispute_rate_trips_above_threshold():
    orders = [make_order(status="manual_review") for _ in range(2)] + [make_order() for _ in range(8)]
    r = tripwires.dispute_rate(make_product(), _FakeDB(orders))  # 20% > 10%
    assert r["tripped"] is True


def test_low_return_rate_within_tolerance():
    orders = [make_order(status="refunded")] + [make_order() for _ in range(9)]  # 10% <= 30%
    assert tripwires.return_rate(make_product(), _FakeDB(orders))["tripped"] is False

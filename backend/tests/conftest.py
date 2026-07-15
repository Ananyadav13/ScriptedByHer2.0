"""Shared pytest fixtures + lightweight object factories.

Most deterministic services touch only a handful of attributes, so we build plain
SimpleNamespace stand-ins (fast, no DB) for unit tests. A seeded-DB session fixture is
provided for the few functions that query (fit_prediction).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

NOW = datetime.utcnow()


def days_ago(d: float) -> datetime:
    return NOW - timedelta(days=d)


def make_review(rating=5, age_days=200, created_days_ago=10, source="manual", text="ok", rid=None):
    return SimpleNamespace(
        id=rid or f"rev_{id(object())}",
        rating=rating,
        reviewer_account_age_days=age_days,
        created_at=days_ago(created_days_ago),
        source=source,
        text=text,
        has_video=False,
        video_path=None,
    )


def make_product(pid="p1", brand="BrandX", category="apparel", price=500, mrp=1000,
                 reviews=None, status="active", seller=None, size_chart_json=None,
                 fabric_claim=None, listing_video_path=None):
    p = SimpleNamespace(
        id=pid, brand=brand, category=category, price=price, mrp=mrp,
        reviews=reviews or [], status=status, seller=seller,
        size_chart_json=size_chart_json, fabric_claim=fabric_claim,
        listing_video_path=listing_video_path, title=f"{brand} {category}",
        qc_requested_at=None, qc_responded=False,
    )
    return p


def make_seller(sid="s1", rating=4.0, account_days=400, case_count=0, products=None,
                trust_flags=None, banned=False):
    return SimpleNamespace(
        id=sid, name=sid, rating=rating, account_created_at=days_ago(account_days),
        case_count=case_count, products=products or [], trust_flags=trust_flags or [],
        banned=banned,
    )


def make_order(oid="o1", otp=1, items=1, hub_anomaly=False, geo=True, hub_id="hub_x",
               buyer_id="b1", product_id="p1", status="delivered"):
    return SimpleNamespace(
        id=oid, otp_scan_count=otp, items_count=items, hub_anomaly_flag=hub_anomaly,
        geo_photo_verified=geo, hub_id=hub_id, buyer_id=buyer_id, product_id=product_id,
        status=status,
    )


@pytest.fixture(scope="module")
def seeded_db():
    """A freshly seeded DB session (module-scoped; read-only tests)."""
    from app.seed import reset_and_seed
    from app.db import SessionLocal
    reset_and_seed()
    db = SessionLocal()
    yield db
    db.close()

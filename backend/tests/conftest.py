"""Shared pytest fixtures + lightweight object factories.

Most deterministic services touch only a handful of attributes, so we build plain
SimpleNamespace stand-ins (fast, no DB) for unit tests. A seeded-DB session fixture and
a TestClient fixture are provided for the tests that need the real stack.

The DATABASE_URL override below MUST run before anything imports `app.config`, because
`app.db` builds its engine from the settings at import time. Without it the suite would
drop and reseed the developer's working database on every run.
"""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_build_trust.db"
os.environ["SEED_RESET"] = "true"

from datetime import timedelta          # noqa: E402  (import after the env override)
from types import SimpleNamespace       # noqa: E402

import pytest                           # noqa: E402

from app.time_utils import utcnow       # noqa: E402

NOW = utcnow()


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


@pytest.fixture(scope="module")
def client(request):
    """TestClient over the real app on a freshly seeded test database.

    Every LLM entry point is stubbed out: these are endpoint smoke tests, so they must
    run offline, deterministically, and without spending Gemini quota. `run_investigation`
    is what FastAPI's BackgroundTasks would otherwise execute synchronously once the
    response is returned — leaving it live would fire a real agent loop per request.
    """
    from fastapi.testclient import TestClient

    from app import seed
    from app.agents import agent2
    from app.main import app
    from app.routers import catalog, disputes, investigations

    mp = pytest.MonkeyPatch()

    def _no_llm_investigation(*args, **kwargs):
        return None

    mp.setattr(disputes, "run_investigation", _no_llm_investigation)
    mp.setattr(investigations, "run_investigation", _no_llm_investigation)
    mp.setattr(catalog, "run_investigation", _no_llm_investigation, raising=False)
    # Agent 2's two LLM calls: clustering and fix drafting. Both already degrade
    # gracefully in production; here we pin them so /audit is fully deterministic.
    mp.setattr(agent2, "cluster_reviews", lambda pid, db: {"dominant": None, "clusters": []})
    mp.setattr(agent2, "draft_fix", lambda p, cluster, db: None)

    seed.reset_and_seed()
    with TestClient(app) as c:
        yield c
    mp.undo()

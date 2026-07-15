"""Mandatory-fields gate tests (Phase 4, task 7). No LLM."""
from __future__ import annotations

from app.services import mandatory_fields as mf

from .conftest import make_product


def test_apparel_needs_size_fabric_and_video():
    p = make_product(category="apparel", size_chart_json=None, fabric_claim=None,
                     listing_video_path=None)
    r = mf.check_product(p)
    assert set(r["required"]) == {"size_chart_json", "fabric_claim", "listing_video_path"}
    assert r["complete"] is False


def test_complete_apparel_listing_passes():
    p = make_product(category="apparel", size_chart_json={"M": "38"}, fabric_claim="cotton",
                     listing_video_path="v.mp4")
    assert mf.check_product(p)["complete"] is True


def test_mug_does_not_need_size_chart():
    # home category: no size chart required, but a fabric claim + video are.
    p = make_product(category="home", size_chart_json=None, fabric_claim="ceramic",
                     listing_video_path="v.mp4")
    r = mf.check_product(p)
    assert "size_chart_json" not in r["required"]
    assert r["complete"] is True


def test_video_always_required():
    p = make_product(category="stationery", listing_video_path=None)
    r = mf.check_product(p)
    assert "listing_video_path" in r["missing"]
    assert r["complete"] is False


def test_new_listing_gate_blocks_incomplete():
    r = mf.check_new_listing({"category": "footwear"})
    assert r["allowed"] is False
    assert "listing_video_path" in r["missing"]
    assert "size_chart_json" in r["missing"]


def test_new_listing_gate_allows_complete():
    r = mf.check_new_listing({
        "category": "footwear", "size_chart_json": {"8": "UK8"},
        "listing_video_path": "v.mp4",
    })
    assert r["allowed"] is True

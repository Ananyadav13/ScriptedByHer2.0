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


def test_bag_needs_real_dimensions_not_free_size():
    # A handbag carries no S/M/L, but "Free Size" alone tells the buyer nothing — this is
    # the listing gap behind real "good quality but small size" complaints.
    p = make_product(category="accessories", size_chart_json={"Free Size": "Free Size"},
                     listing_video_path="v.mp4")
    r = mf.check_product(p)
    assert "size_chart_json" in r["required"]
    assert "size_chart_json" in r["missing"]
    assert r["complete"] is False


def test_bag_with_measurements_passes():
    p = make_product(category="accessories",
                     size_chart_json={"Free Size": "L 30cm x W 12cm x H 26cm"},
                     listing_video_path="v.mp4")
    assert mf.check_product(p)["complete"] is True


def test_free_size_with_a_measurement_is_not_vacuous():
    # a saree is "Free Size" but states its length -> a real spec, must not be flagged
    p = make_product(category="apparel", size_chart_json={"Free Size": "5.5m saree + 0.8m blouse"},
                     fabric_claim="pure silk", listing_video_path="v.mp4")
    assert mf.check_product(p)["complete"] is True


def test_empty_size_chart_still_missing():
    p = make_product(category="accessories", size_chart_json={}, listing_video_path="v.mp4")
    assert "size_chart_json" in mf.check_product(p)["missing"]


def test_new_listing_gate_blocks_incomplete():
    r = mf.check_new_listing({"category": "footwear"})
    assert r["allowed"] is False
    assert "listing_video_path" in r["missing"]
    assert "size_chart_json" in r["missing"]
    # a new listing also needs the descriptive basics
    assert {"title", "description", "color"}.issubset(set(r["missing"]))


def test_new_listing_gate_allows_complete():
    r = mf.check_new_listing({
        "category": "footwear", "size_chart_json": {"8": "UK8"},
        "listing_video_path": "v.mp4",
        "title": "Lightweight Running Shoes", "color": "Blue",
        "description": "Breathable mesh running shoes with a cushioned EVA sole.",
    })
    assert r["allowed"] is True


def test_new_listing_requires_a_real_description():
    r = mf.check_new_listing({
        "category": "home", "listing_video_path": "v.mp4", "fabric_claim": "cotton",
        "title": "Nice Mug", "color": "White", "description": "nice",  # too short
    })
    assert r["allowed"] is False
    assert "description" in r["missing"]


def test_new_listing_descriptive_fields_alone_are_not_enough():
    # title/description/color present, but the media gate still applies
    r = mf.check_new_listing({
        "category": "apparel", "title": "Cotton Kurti", "color": "Black",
        "description": "A comfortable pure-cotton anarkali kurti for daily wear.",
    })
    assert r["allowed"] is False
    assert "listing_video_path" in r["missing"]

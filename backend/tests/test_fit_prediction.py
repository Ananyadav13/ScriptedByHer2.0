"""Fit-prediction tests: drift math both directions + no-history fallback (Phase 4, task 7).

`predict_size` is a PURE join — these tests never touch the LLM."""
from __future__ import annotations

from app.services import fit_prediction as fp


# ---- drift shift math, both directions ----
def test_numeric_runs_small_sizes_up():
    # delta -1 = brand runs 1 size small -> buyer should go UP one size.
    assert fp._shift_numeric("8", -1.0) == "9"


def test_numeric_runs_large_sizes_down():
    assert fp._shift_numeric("8", 1.0) == "7"


def test_letter_runs_small_sizes_up():
    assert fp._shift_letter("M", -1.0) == "L"


def test_letter_runs_large_sizes_down():
    assert fp._shift_letter("M", 1.0) == "S"


def test_letter_ladder_clamps_at_ends():
    assert fp._shift_letter("XXXL", -1.0) == "XXXL"   # cannot go above the top
    assert fp._shift_letter("XS", 1.0) == "XS"        # cannot go below the bottom


# ---- full join against the seeded DB ----
def test_history_plus_drift(seeded_db):
    r = fp.predict_size("buyer_normal", "prod_size_shoes", seeded_db)
    assert r["original"] == "8"
    assert r["adjusted"] == "9"                       # StepUp footwear runs 1 small
    assert r["source"] == "history+drift"
    assert "1 size small" in r["explanation"]
    assert "214" in r["explanation"]


def test_drift_only_without_history(seeded_db):
    # serial claimer has no kept-size history -> anchors on the drift's own label_size.
    r = fp.predict_size("buyer_serial_claimer", "prod_size_shoes", seeded_db)
    assert r["source"] == "drift_only"
    assert r["adjusted"] == "9"


def test_no_history_no_drift_fallback(seeded_db):
    # a mug: no size drift, buyer has no relevant history -> adjust nothing.
    r = fp.predict_size("buyer_serial_claimer", "prod_normal_mug", seeded_db)
    assert r["source"] == "no_history"
    assert r["adjusted"] is None
    assert r["drift_delta"] == 0.0


def test_missing_product_returns_error(seeded_db):
    assert "error" in fp.predict_size("buyer_normal", "does_not_exist", seeded_db)

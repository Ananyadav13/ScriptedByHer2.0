"""Deterministic fit prediction — a pure JOIN, NO LLM.

Given a buyer and a product, predict the size that will actually fit by combining:
  1. the buyer's own KEPT-size history (sizes they bought and did NOT return), and
  2. the crowd-sourced SIZE-DRIFT table for that brand+category (how much the brand's
     labels run large/small, learned from returns).

This is intentionally LLM-free — size fit is a measurable join, not a judgement call,
so it stays fast, free, and explainable. The endpoint (`GET /fit`) proves via server
logs that no model call happens on this path. Enforced by having zero LLM imports here.
"""
from __future__ import annotations

from ..models import Buyer, Product, SizeDrift


# apparel/footwear sizes we can step up or down along an ordered ladder.
_NUMERIC = "numeric"        # footwear etc. — the label IS a number ("8")
_LETTER = "letter"          # apparel — S/M/L/XL ladder
_LETTER_LADDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]


def _history_key(product: Product) -> str:
    return f"{product.brand}:{product.category}"


def _kind(label: str) -> str:
    return _NUMERIC if str(label).strip().isdigit() else _LETTER


def _shift_numeric(label: str, delta: float) -> str:
    """Shift a numeric size by `delta` whole steps (delta<0 = size runs small -> size up)."""
    # brand runs `delta` small  =>  buyer should go UP by |delta| to compensate.
    adjusted = int(round(float(label) - delta))
    return str(adjusted)


def _shift_letter(label: str, delta: float) -> str:
    label = str(label).upper()
    if label not in _LETTER_LADDER:
        return label
    idx = _LETTER_LADDER.index(label)
    # runs small (delta<0) -> move up the ladder (higher index) to compensate.
    new_idx = min(max(idx - int(round(delta)), 0), len(_LETTER_LADDER) - 1)
    return _LETTER_LADDER[new_idx]


def predict_size(buyer_id: str, product_id: str, db) -> dict:
    """Predict the fitting size for `buyer_id` on `product_id`.

    Returns {original, adjusted, explanation, drift_delta, sample_size, source}.
    `original` = the buyer's usual size for this brand/category (or a generic fallback);
    `adjusted` = that size shifted by the brand's measured drift. When there is no
    history AND no drift, we return a no-history fallback that adjusts nothing.
    """
    buyer = db.get(Buyer, buyer_id)
    product = db.get(Product, product_id)
    if product is None:
        return {"error": f"product {product_id} not found"}

    history = (buyer.kept_size_history_json or {}) if buyer else {}
    # 1) the buyer's usual size: exact brand:category, else a generic:category fallback.
    original = history.get(_history_key(product)) or history.get(f"generic:{product.category}")
    have_history = original is not None

    # 2) the brand+category size drift (crowd-learned from returns).
    drift = (
        db.query(SizeDrift)
        .filter(SizeDrift.brand == product.brand, SizeDrift.category == product.category)
        .first()
    )

    if not have_history and drift is None:
        return {
            "buyer_id": buyer_id,
            "product_id": product_id,
            "original": None,
            "adjusted": None,
            "drift_delta": 0.0,
            "sample_size": 0,
            "source": "no_history",
            "explanation": (
                "No purchase history for you and no fit data for this brand yet — "
                "pick your usual size; we'll learn as more buyers report fit."
            ),
        }

    # If we have drift but no personal history, adjust the drift's own label_size as the anchor.
    if not have_history:
        original = drift.label_size

    delta = drift.true_measurement_delta if drift else 0.0
    sample = drift.sample_size if drift else 0

    if delta == 0.0:
        adjusted = original
    elif _kind(original) == _NUMERIC:
        adjusted = _shift_numeric(original, delta)
    else:
        adjusted = _shift_letter(original, delta)

    if delta == 0.0:
        explanation = f"This brand's sizing is true to label — your usual {original} should fit."
    else:
        direction = "small" if delta < 0 else "large"
        magnitude = abs(delta)
        step_word = "size" if magnitude == 1 else "sizes"
        explanation = (
            f"This brand runs {magnitude:g} {step_word} {direction} based on {sample} returns — "
            f"we suggest {adjusted} instead of your usual {original}."
        )

    return {
        "buyer_id": buyer_id,
        "product_id": product_id,
        "original": original,
        "adjusted": adjusted,
        "drift_delta": delta,
        "sample_size": sample,
        "source": "history+drift" if have_history and drift else
                  "drift_only" if drift else "history_only",
        "explanation": explanation,
    }

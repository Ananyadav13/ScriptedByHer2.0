"""Deterministic tripwires — NO LLM.

The "event-driven, not polling" model: cheap deterministic watchers scan the
catalogue; when one trips, the caller FIRES an Agent-1 investigation (`run_investigation`).
That is what makes Agent 1 feel real-time without burning the free-tier quota on a poll loop.

Three watchers, all reading `rules.py` constants:
  - rating drop:  last-30d trustworthy rating falls >= RATING_DROP_ALERT vs the prior 30d
  - return rate:  recent refunded/RTO share > RETURN_RATE_ALERT
  - dispute rate: recent disputed-order share > DISPUTE_RATE_ALERT
"""
from __future__ import annotations

from ..models import Order, Product
from ..time_utils import utcnow
from .rules import (
    DISPUTE_RATE_ALERT,
    NEW_ACCOUNT_AGE_DAYS,
    RATING_DROP_ALERT,
    RATING_TREND_WINDOW_DAYS,
    RETURN_RATE_ALERT,
)


def _windowed_rating(product: Product, start_days_ago: float, end_days_ago: float) -> tuple[float | None, int]:
    """Plain avg rating of genuine (established-account) reviews created within the
    (end_days_ago, start_days_ago] window. Returns (avg or None, count)."""
    now = utcnow()
    total = 0.0
    n = 0
    for r in product.reviews:
        if r.reviewer_account_age_days < NEW_ACCOUNT_AGE_DAYS:
            continue  # discount the manipulable new-account cluster (same rule as trustworthy_rating)
        age = (now - r.created_at).days
        if end_days_ago < age <= start_days_ago:
            total += r.rating
            n += 1
    return (round(total / n, 2), n) if n else (None, 0)


def rating_drop(product: Product) -> dict:
    """Trustworthy rating deteriorating: last-window avg vs prior-window avg."""
    w = RATING_TREND_WINDOW_DAYS
    recent, rn = _windowed_rating(product, w, 0)
    prior, pn = _windowed_rating(product, 2 * w, w)
    drop = (prior - recent) if (recent is not None and prior is not None) else 0.0
    tripped = drop >= RATING_DROP_ALERT
    return {
        "signal": "rating_drop",
        "recent_rating": recent, "recent_count": rn,
        "prior_rating": prior, "prior_count": pn,
        "drop": round(drop, 2), "threshold": RATING_DROP_ALERT,
        "tripped": tripped,
        "reason": (f"trustworthy rating fell {drop:.2f} ({prior}->{recent}) over the last {w}d "
                   f">= {RATING_DROP_ALERT} alert" if tripped else
                   f"rating stable ({prior}->{recent})" if recent is not None and prior is not None
                   else "not enough windowed reviews to compare"),
    }


def _order_rates(product: Product, db) -> tuple[int, int, int]:
    """(total, refunded, disputed) order counts for a product."""
    orders = db.query(Order).filter(Order.product_id == product.id).all()
    total = len(orders)
    refunded = sum(1 for o in orders if o.status == "refunded")
    disputed = sum(1 for o in orders if o.status == "manual_review")
    return total, refunded, disputed


def return_rate(product: Product, db) -> dict:
    total, refunded, _ = _order_rates(product, db)
    rate = (refunded / total) if total else 0.0
    tripped = total > 0 and rate > RETURN_RATE_ALERT
    return {
        "signal": "return_rate", "total_orders": total, "refunded": refunded,
        "rate": round(rate, 3), "threshold": RETURN_RATE_ALERT, "tripped": tripped,
        "reason": (f"{refunded}/{total} orders refunded ({rate:.0%}) > {RETURN_RATE_ALERT:.0%} alert"
                   if tripped else f"{refunded}/{total} refunded ({rate:.0%}) within tolerance"),
    }


def dispute_rate(product: Product, db) -> dict:
    total, _, disputed = _order_rates(product, db)
    rate = (disputed / total) if total else 0.0
    tripped = total > 0 and rate > DISPUTE_RATE_ALERT
    return {
        "signal": "dispute_rate", "total_orders": total, "disputed": disputed,
        "rate": round(rate, 3), "threshold": DISPUTE_RATE_ALERT, "tripped": tripped,
        "reason": (f"{disputed}/{total} orders disputed ({rate:.0%}) > {DISPUTE_RATE_ALERT:.0%} alert"
                   if tripped else f"{disputed}/{total} disputed ({rate:.0%}) within tolerance"),
    }


def scan_product(product: Product, db) -> dict:
    """Run all three watchers over one product. Returns the signals + which tripped."""
    signals = [rating_drop(product), return_rate(product, db), dispute_rate(product, db)]
    tripped = [s for s in signals if s["tripped"]]
    return {
        "product_id": product.id,
        "signals": signals,
        "tripped": [s["signal"] for s in tripped],
        "should_investigate": bool(tripped),
    }


def scan_catalogue(db) -> list[dict]:
    """Sweep every active product; return only those with a tripped watcher."""
    out = []
    for p in db.query(Product).filter(Product.status == "active").all():
        result = scan_product(p, db)
        if result["should_investigate"]:
            out.append(result)
    return out

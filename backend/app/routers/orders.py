"""Buyer 'My Orders' surface.

Orders belong to a BUYER, not to a product page — this is where a buyer sees what they
bought and opens a dispute. Each order carries the SAME claim-history context the dispute
agent will use (e.g. a serial claimer's disputes route to manual review), so the buyer-facing
copy and the agent's decision never disagree. Read-only; disputes are still opened via /dispute.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Buyer, Hub, Order, Product, ProductVariant
from ..services import risk_checks
from ..services.rules import SERIAL_CLAIM_COUNT

router = APIRouter(tags=["orders"])

# bulk volume orders (order_cf_*, order_sw_*) exist only to clear the confidence floor —
# they are not real buyer purchases and must not clutter a My Orders view.
_VOLUME_PREFIXES = ("order_cf_", "order_sw_")


def _claim_context(buyer: Buyer | None) -> dict:
    """The buyer's claim standing — identical to what the dispute agent reads."""
    count = (buyer.claim_history or {}).get("count", 0) if buyer else 0
    serial = count >= SERIAL_CLAIM_COUNT
    return {
        "claim_count": count,
        "is_serial_claimer": serial,
        "note": (
            f"You've filed {count} prior claims. To keep things fair, a new dispute is routed "
            f"to a human for manual review rather than auto-approved."
            if serial else
            f"You've filed {count} prior claims — disputes are handled on their merits."
            if count else
            "Clean claim history — disputes are handled on the delivery evidence."
        ),
    }


def _order_view(o: Order, db: Session) -> dict:
    p = db.get(Product, o.product_id)
    variant = db.get(ProductVariant, o.variant_id) if o.variant_id else None
    hub = db.get(Hub, o.hub_id) if o.hub_id else None
    buyer = db.get(Buyer, o.buyer_id)

    # deterministic agent "reaction" preview — what a dispute on THIS order would trigger,
    # so the buyer sees the reasoning before opening it (and it matches the agent trace).
    sig = risk_checks.delivery_signals(o, buyer, hub)
    if o.status == "manual_review":
        reaction = {"route": "manual_review", "tone": "amber",
                    "label": "Under manual review — a manager is checking this claim"}
    elif sig["claimer_classification"] == "serial":
        reaction = {"route": "manual_review", "tone": "amber",
                    "label": "A dispute here goes to manual review (serial-claim history)"}
    elif sig["corroborated"]:
        reaction = {"route": "refund_fast_track", "tone": "teal",
                    "label": f"{sig['independent_signal_count']} independent delivery signals — a dispute fast-tracks a refund"}
    elif o.claim_type in ("fabric_mismatch", "item_not_as_described"):
        reaction = {"route": "recommend_review", "tone": "brand",
                    "label": "Material dispute → an advisory review by a manager (media is uncertain)"}
    else:
        reaction = {"route": "standard_process", "tone": "neutral",
                    "label": "Standard dispute handling"}

    return {
        "id": o.id,
        "product_id": o.product_id,
        "product_title": p.title if p else o.product_id,
        "price": p.price if p else None,
        "variant": variant.name if variant else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "status": o.status,
        "claim_type": o.claim_type,
        "hub_name": hub.name if hub else None,
        "dispute_available": o.status == "delivered",
        "reaction": reaction,
    }


@router.get("/buyers")
def list_buyers(db: Session = Depends(get_db)):
    """The demo buyers, each with a one-line claim standing (drives the My Orders switcher)."""
    out = []
    for b in db.query(Buyer).all():
        n_orders = (
            db.query(Order)
            .filter(Order.buyer_id == b.id)
            .filter(~Order.id.startswith(_VOLUME_PREFIXES[0]))
            .filter(~Order.id.startswith(_VOLUME_PREFIXES[1]))
            .count()
        )
        ctx = _claim_context(b)
        out.append({
            "id": b.id,
            "name": "You (clean history)" if not ctx["claim_count"] else f"Repeat claimant ({ctx['claim_count']} claims)",
            "claim_count": ctx["claim_count"],
            "is_serial_claimer": ctx["is_serial_claimer"],
            "order_count": n_orders,
        })
    return out


@router.get("/buyers/{buyer_id}/orders")
def buyer_orders(buyer_id: str, db: Session = Depends(get_db)):
    buyer = db.get(Buyer, buyer_id)
    if not buyer:
        raise HTTPException(404, "buyer not found")
    orders = (
        db.query(Order)
        .filter(Order.buyer_id == buyer_id)
        .order_by(Order.delivered_at.desc())
        .all()
    )
    items = [_order_view(o, db) for o in orders
             if not o.id.startswith(_VOLUME_PREFIXES)]
    return {
        "buyer_id": buyer_id,
        "claim_context": _claim_context(buyer),
        "order_count": len(items),
        "orders": items,
    }

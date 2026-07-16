"""Investigation API: kick off Agent 1, read status/log/verdict."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import events
from ..agents.agent1_tools import dispatch
from ..agents.orchestrator import run_investigation
from ..db import get_db
from ..models import Investigation, Order, Product

router = APIRouter(tags=["investigations"])


class InvestigateIn(BaseModel):
    product_id: str | None = None
    trigger: str = "pre_purchase"          # pre_purchase | catalog_gate | post_delivery
    order_id: str | None = None


@router.post("/investigate")
def investigate(body: InvestigateIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    if not body.product_id and not body.order_id:
        raise HTTPException(400, "product_id or order_id required")

    inv_id = f"inv_{uuid.uuid4().hex[:12]}"
    db.add(Investigation(
        id=inv_id,
        product_id=body.product_id,
        order_id=body.order_id,
        trigger=body.trigger,
        status="queued",
        tool_calls_log_json=[],
        created_at=datetime.utcnow(),
    ))
    db.commit()

    # Create the event queue BEFORE the task starts so an SSE client that
    # connects immediately never misses the opening events.
    events.create(inv_id)
    background.add_task(run_investigation, inv_id, body.product_id, body.trigger, body.order_id)
    return {"investigation_id": inv_id, "status": "queued"}


@router.get("/investigations")
def list_investigations(limit: int = 25, db: Session = Depends(get_db)):
    """Recent Agent-1 investigations (activity log). Newest first, with a verdict summary."""
    rows = (
        db.query(Investigation)
        .order_by(Investigation.created_at.desc())
        .limit(limit)
        .all()
    )
    from ..models import Manager, Seller
    out = []
    for inv in rows:
        p = db.get(Product, inv.product_id) if inv.product_id else None
        seller = db.get(Seller, p.seller_id) if p else None
        manager = db.get(Manager, seller.manager_id) if seller and seller.manager_id else None
        v = inv.verdict_json or {}
        out.append({
            "id": inv.id,
            "product_id": inv.product_id,
            "product_title": p.title if p else None,
            "seller_id": p.seller_id if p else None,
            "seller_name": seller.name if seller else None,
            "manager": manager.name if manager else None,
            "order_id": inv.order_id,
            "trigger": inv.trigger,
            "status": inv.status,
            "tool_count": len(inv.tool_calls_log_json or []),
            "decision": v.get("decision"),
            "action": v.get("action"),
            "confidence": v.get("confidence"),
            "evidence": v.get("evidence", []),
            "buyer_explanation": v.get("buyer_explanation"),
            "created_at": inv.created_at.isoformat(),
        })
    return {"count": len(out), "investigations": out}


# ---------------------------------------------------------------------------
# GET /agent1/evidence — the DETERMINISTIC "always-watching" layer (NO LLM).
# Runs Agent 1's non-LLM tools so the evidence is visible even without quota;
# the LLM only reasons over these on a trigger (PLAN §5A).
# ---------------------------------------------------------------------------
def _items_from_catalog(c: dict) -> list[dict]:
    items = []
    for key, label in (("price_mrp", "Price vs MRP"), ("review_burst", "Review burst"),
                        ("image_match", "Image authenticity")):
        s = c.get(key) or {}
        if s.get("reason"):
            items.append({"label": label, "flag": bool(s.get("flag")), "detail": s["reason"]})
    tr = c.get("trustworthy_rating") or {}
    if tr.get("reason"):
        items.append({"label": "Trustworthy rating", "flag": not tr.get("sufficient", True),
                      "detail": tr["reason"]})
    return items


@router.get("/agent1/evidence")
def agent1_evidence(product_id: str | None = None, order_id: str | None = None,
                    db: Session = Depends(get_db)):
    if not product_id and order_id:
        o = db.get(Order, order_id)
        product_id = o.product_id if o else None
    if not product_id:
        raise HTTPException(400, "product_id or order_id required")
    if not db.get(Product, product_id):
        raise HTTPException(404, "product not found")

    tools = []
    cat = dispatch("check_catalog_risk", {"product_id": product_id}, db)
    tools.append({"tool": "check_catalog_risk", "signals": _items_from_catalog(cat)})
    seller = dispatch("check_seller_profile", {"product_id": product_id}, db)
    if "error" not in seller:
        tools.append({"tool": "check_seller_profile", "signals": [
            {"label": "Seller profile", "flag": bool(seller.get("flag")), "detail": seller.get("reason")}
        ]})
    if order_id:
        dsig = dispatch("check_delivery_signals", {"order_id": order_id}, db)
        if "error" not in dsig:
            tools.append({"tool": "check_delivery_signals", "signals": [
                {"label": "Delivery signals", "flag": bool(dsig.get("flag")), "detail": dsig.get("reason")}
            ]})

    flags = sum(1 for t in tools for s in t["signals"] if s["flag"])
    return {"product_id": product_id, "order_id": order_id, "risk_flags": flags, "tools": tools}


@router.get("/investigations/{investigation_id}")
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "investigation not found")
    return {
        "id": inv.id,
        "product_id": inv.product_id,
        "order_id": inv.order_id,
        "trigger": inv.trigger,
        "status": inv.status,
        "tool_calls_log": inv.tool_calls_log_json,
        "verdict": inv.verdict_json,
    }

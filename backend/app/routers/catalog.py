"""Agent 2 surface — Listing & Catalog Integrity (Phase 4).

Endpoints the frontend (Phase 5) consumes:
  GET  /fit                              — deterministic size prediction (proves NO LLM on this path)
  POST /audit                            — sweep catalogue -> delisting engine (+ clustering on a trip)
  GET  /admin/actions                    — the catalog-action queue (tier badges, reasons)
  GET  /seller/{id}/drafts               — pending fix drafts (before/after) for a seller
  POST /catalog_actions/{id}/approve     — seller approves a draft -> applies it to the product
  POST /listing/check                    — mandatory-fields gate for a NEW listing (Phase 5 flow)
  POST /tripwires/scan                   — deterministic watchers -> FIRE Agent-1 investigations

The delisting/tripwire/fit logic is deterministic (services/); clustering + fix drafting are the
LLM half (agents/agent2.py) and degrade gracefully so the audit always completes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import agent2, events
from ..agents.orchestrator import run_investigation
from ..db import get_db
from ..models import CatalogAction, Investigation, Notification, Product
from ..services import delisting, fit_prediction, mandatory_fields, tripwires

router = APIRouter(tags=["catalog"])


def _notify(db: Session, audience: str, subject: str, body: str,
            priority: str = "normal", related_id: str | None = None) -> None:
    db.add(Notification(
        id=f"ntf_{uuid.uuid4().hex[:12]}", audience=audience, subject=subject,
        body=body, priority=priority, related_id=related_id, created_at=datetime.utcnow(),
    ))


def _log(db: Session, product_id: str, action: str, evidence: dict) -> CatalogAction:
    row = CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}", product_id=product_id, action=action,
        evidence_json=evidence, seller_approved=False, created_at=datetime.utcnow(),
    )
    db.add(row)
    return row


def _apply_penalty(seller, penalty: dict | None) -> None:
    if seller and penalty and penalty.get("penalty"):
        seller.rating = max(0.0, round((seller.rating or 0.0) - penalty["penalty"], 2))


# ---------------------------------------------------------------------------
# GET /fit — deterministic size prediction (NO LLM)
# ---------------------------------------------------------------------------
@router.get("/fit")
def fit(buyer_id: str, product_id: str, db: Session = Depends(get_db)):
    result = fit_prediction.predict_size(buyer_id, product_id, db)
    if "error" in result:
        raise HTTPException(404, result["error"])
    print(f"[fit] {buyer_id} x {product_id}: {result['original']} -> {result['adjusted']} "
          f"(NO LLM — pure join)")
    return result


# ---------------------------------------------------------------------------
# POST /audit — the Agent-2 catalogue sweep
# ---------------------------------------------------------------------------
class AuditIn(BaseModel):
    cluster: bool = True   # run LLM clustering where a tier trips (set False for a fast/offline sweep)


@router.post("/audit")
def run_audit(body: AuditIn | None = None, db: Session = Depends(get_db)):
    cluster = True if body is None else body.cluster
    products = db.query(Product).filter(Product.status.in_(("active", "flagged"))).all()
    summary = {"suspended": 0, "correction_window": 0, "logistics_referral": 0,
               "fix_drafts": 0, "kept": 0}
    items = []

    for p in products:
        ev = delisting.evaluate_delisting(p)
        clusters = None

        if ev["delist"] and cluster:
            # a tier tripped: run the richer LLM clustering (graceful) to refine routing/summary.
            clusters = agent2.cluster_reviews(p.id, db)
            dom = clusters.get("dominant")
            if dom:
                ev = delisting.evaluate_delisting(p, dominant_label=dom["label"])

        if not ev["delist"]:
            summary["kept"] += 1
            items.append({**ev, "applied": "keep"})
            continue

        seller = p.seller
        action = ev["action"]
        if action == "suspend":
            p.status = "suspended"
            if seller:
                seller.case_count = (seller.case_count or 0) + 1
            _apply_penalty(seller, ev["seller_penalty"])
            _log(db, p.id, "suspend", {"decision": "delist_suspend", "evidence": [ev["reason"]],
                                       "tier": ev["tier_label"], "seller_penalty": ev["seller_penalty"]})
            _notify(db, "seller", "Listing suspended (fraud/quality)",
                    f"{p.title}: {ev['reason']}", "immediate", p.id)
            summary["suspended"] += 1

        elif action == "correction_window":
            p.status = "correction_window"
            _apply_penalty(seller, ev["seller_penalty"])
            _log(db, p.id, "correction", {"decision": "correction_window", "evidence": [ev["reason"]],
                                          "tier": ev["tier_label"], "seller_penalty": ev["seller_penalty"]})
            if ev.get("fixable"):
                dom_cluster = (clusters or {}).get("dominant") or {
                    "label": ev["dominant_label"], "summary": ev["dominant_label"],
                    "agreement": ev["agreement"]}
                draft = agent2.draft_fix(p, dom_cluster, db)
                if draft is not None:
                    summary["fix_drafts"] += 1
            _notify(db, "seller", "Listing in correction window — fix required",
                    f"{p.title}: {ev['reason']}", "high", p.id)
            summary["correction_window"] += 1

        elif action == "logistics_referral":
            # delivery fault: the hub's problem, not the seller's -> refer, NO seller penalty.
            _log(db, p.id, "logistics_referral", {"decision": "logistics_referral",
                                                  "evidence": [ev["reason"]], "tier": ev["tier_label"]})
            _notify(db, "ops", "Delivery-fault cluster — logistics referral",
                    f"{p.title}: {ev['reason']}", "high", p.id)
            summary["logistics_referral"] += 1

        items.append({**ev, "applied": action, "clusters": clusters["clusters"] if clusters else None})

    db.commit()
    return {"summary": summary, "evaluated": len(products), "items": items}


# ---------------------------------------------------------------------------
# GET /admin/actions — the action queue
# ---------------------------------------------------------------------------
@router.get("/admin/actions")
def admin_actions(action: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(CatalogAction).order_by(CatalogAction.created_at.desc())
    if action:
        q = q.filter(CatalogAction.action == action)
    rows = q.limit(limit).all()
    out = []
    for a in rows:
        p = db.get(Product, a.product_id)
        ev = a.evidence_json or {}
        out.append({
            "id": a.id, "product_id": a.product_id,
            "product_title": p.title if p else None,
            "seller_id": p.seller_id if p else None,
            "action": a.action, "tier": ev.get("tier"),
            "decision": ev.get("decision"), "reason": "; ".join(ev.get("evidence", [])) or None,
            "seller_approved": a.seller_approved,
            "created_at": a.created_at.isoformat(),
        })
    return {"count": len(out), "actions": out}


# ---------------------------------------------------------------------------
# GET /seller/{id}/drafts  +  POST /catalog_actions/{id}/approve
# ---------------------------------------------------------------------------
@router.get("/seller/{seller_id}/drafts")
def seller_drafts(seller_id: str, db: Session = Depends(get_db)):
    product_ids = [p.id for p in db.query(Product).filter(Product.seller_id == seller_id).all()]
    rows = (
        db.query(CatalogAction)
        .filter(CatalogAction.action == "fix_draft",
                CatalogAction.product_id.in_(product_ids),
                CatalogAction.seller_approved.is_(False))
        .order_by(CatalogAction.created_at.desc())
        .all()
    )
    return {"seller_id": seller_id, "count": len(rows), "drafts": [
        {"id": a.id, "product_id": a.product_id, "field": (a.evidence_json or {}).get("field"),
         "cluster": (a.evidence_json or {}).get("cluster"),
         "summary": (a.evidence_json or {}).get("summary"),
         "before": (a.evidence_json or {}).get("before"),
         "after": (a.evidence_json or {}).get("after"),
         "rationale": (a.evidence_json or {}).get("rationale"),
         "created_at": a.created_at.isoformat()}
        for a in rows
    ]}


@router.post("/catalog_actions/{action_id}/approve")
def approve_draft(action_id: str, db: Session = Depends(get_db)):
    a = db.get(CatalogAction, action_id)
    if not a:
        raise HTTPException(404, "catalog action not found")
    if a.action != "fix_draft":
        raise HTTPException(400, f"action {action_id} is '{a.action}', not a fix_draft")
    if a.seller_approved:
        raise HTTPException(400, "draft already approved")

    p = db.get(Product, a.product_id)
    if not p:
        raise HTTPException(404, "product not found")

    after = (a.evidence_json or {}).get("after", {})
    applied = {}
    if "size_chart_json" in after and after["size_chart_json"] is not None:
        p.size_chart_json = after["size_chart_json"]
        applied["size_chart_json"] = after["size_chart_json"]
    if after.get("fabric_claim"):
        p.fabric_claim = after["fabric_claim"]
        applied["fabric_claim"] = after["fabric_claim"]

    a.seller_approved = True
    # a corrected listing comes off the correction window and goes back live.
    if p.status == "correction_window":
        p.status = "active"
    _log(db, p.id, "fix_applied", {"decision": "fix_applied", "from_draft": a.id, "applied": applied})
    db.commit()
    return {"action_id": a.id, "product_id": p.id, "applied": applied, "new_status": p.status}


# ---------------------------------------------------------------------------
# POST /listing/check — mandatory-fields gate for a NEW listing (Phase 5)
# ---------------------------------------------------------------------------
class NewListingIn(BaseModel):
    category: str
    size_chart_json: dict | None = None
    fabric_claim: str | None = None
    listing_video_path: str | None = None


@router.post("/listing/check")
def listing_check(body: NewListingIn):
    return mandatory_fields.check_new_listing(body.model_dump())


# ---------------------------------------------------------------------------
# POST /tripwires/scan — deterministic watchers FIRE Agent-1 investigations
# ---------------------------------------------------------------------------
class TripwireScanIn(BaseModel):
    fire: bool = True   # actually launch Agent-1 investigations for tripped products


@router.post("/tripwires/scan")
def tripwire_scan(body: TripwireScanIn | None, background: BackgroundTasks,
                  db: Session = Depends(get_db)):
    fire = True if body is None else body.fire
    tripped = tripwires.scan_catalogue(db)
    fired = []
    for t in tripped:
        if not fire:
            continue
        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        db.add(Investigation(
            id=inv_id, product_id=t["product_id"], order_id=None, trigger="tripwire",
            status="queued", tool_calls_log_json=[], created_at=datetime.utcnow(),
        ))
        db.commit()
        events.create(inv_id)
        background.add_task(run_investigation, inv_id, t["product_id"], "tripwire", None)
        fired.append({"product_id": t["product_id"], "investigation_id": inv_id,
                      "tripped": t["tripped"]})
    return {"tripped_count": len(tripped), "tripped": tripped, "fired": fired}

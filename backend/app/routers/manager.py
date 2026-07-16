"""Business-manager governance.

Every product the agents lock/hold/suspend lands in the owning manager's review
queue. The ABSOLUTE decision — unlock, confirm the lock, or delete — lies with the
manager (a human), not the agent. ~100 sellers map to one manager.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CatalogAction, Manager, Product, Seller
from ..services import delisting

router = APIRouter(tags=["manager"])

_ISSUE_STATUSES = {"locked", "on_hold", "suspended", "needs_info", "flagged", "correction_window", "delisted"}

# statuses that represent an agent action awaiting managerial review.
# `flagged`/`needs_info` are ADVISORY (sale continues); locked/on_hold/suspended are protective.
_QUEUE_STATUSES = {"locked", "on_hold", "suspended", "needs_info", "flagged"}


@router.get("/managers")
def list_managers(db: Session = Depends(get_db)):
    return [
        {"id": m.id, "name": m.name, "seller_count": len(m.sellers)}
        for m in db.query(Manager).all()
    ]


@router.get("/manager/{manager_id}/queue")
def manager_queue(manager_id: str, db: Session = Depends(get_db)):
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
    seller_ids = [s.id for s in manager.sellers]
    products = (
        db.query(Product)
        .filter(Product.seller_id.in_(seller_ids), Product.status.in_(_QUEUE_STATUSES))
        .all()
    )
    out = []
    for p in products:
        last = (
            db.query(CatalogAction)
            .filter(CatalogAction.product_id == p.id)
            .order_by(CatalogAction.created_at.desc())
            .first()
        )
        out.append({
            "product_id": p.id,
            "title": p.title,
            "seller_id": p.seller_id,
            "status": p.status,
            "agent_action": last.action if last else None,
            "evidence": last.evidence_json if last else None,
            "acted_at": last.created_at.isoformat() if last else None,
        })
    return {"manager_id": manager_id, "queue_size": len(out), "items": out}


@router.get("/manager/{manager_id}/sellers")
def manager_sellers(manager_id: str, db: Session = Depends(get_db)):
    """The book of sellers this manager owns, each with their products + the dominant
    complaint + current status — so a manager sees WHO they manage and WHAT's wrong."""
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
    from datetime import datetime

    _CLABEL = {"size_issue": "Size / fit", "fabric_mismatch": "Fabric mismatch",
               "damaged_delivery": "Delivery damage", "possible_fraud": "Fraud / quality",
               "other": "Assorted"}
    out = []
    for s in sorted(manager.sellers, key=lambda x: (x.rating or 0)):
        prods = db.query(Product).filter(Product.seller_id == s.id).all()
        pitems = []
        for p in prods:
            revs = p.reviews or []
            avg = round(sum(r.rating for r in revs) / len(revs), 1) if revs else None
            cl = delisting.classify_complaints(p)
            complaint = None
            if cl["dominant"] and cl["negative_count"] > 0:
                complaint = {"label": _CLABEL.get(cl["dominant"], cl["dominant"]),
                             "agreement": cl["agreement"], "count": cl["negative_count"]}
            pitems.append({
                "product_id": p.id, "title": p.title, "status": p.status,
                "rating": avg, "review_count": len(revs), "complaint": complaint,
                "needs_action": p.status in _ISSUE_STATUSES,
            })
        pitems.sort(key=lambda x: (0 if x["needs_action"] else 1))
        age = (datetime.utcnow() - s.account_created_at).days if s.account_created_at else None
        out.append({
            "seller_id": s.id, "name": s.name, "rating": s.rating,
            "trust_flags": s.trust_flags or [], "case_count": s.case_count or 0,
            "account_age_days": age, "banned": bool(getattr(s, "banned", False)),
            "product_count": len(prods),
            "flagged_count": sum(1 for x in pitems if x["needs_action"]),
            "products": pitems,
        })
    # riskiest sellers first (low rating / more flags)
    out.sort(key=lambda x: (-x["flagged_count"], x["rating"] or 0))
    return {"manager_id": manager_id, "name": manager.name, "seller_count": len(out), "sellers": out}


class ManagerDecision(BaseModel):
    decision: str  # unlock | confirm_lock | delete


@router.post("/manager/{manager_id}/products/{product_id}/decision")
def manager_decide(manager_id: str, product_id: str, body: ManagerDecision,
                   db: Session = Depends(get_db)):
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "product not found")
    # governance: a manager may only act on their own sellers' products
    seller = db.get(Seller, product.seller_id)
    if not seller or seller.manager_id != manager_id:
        raise HTTPException(403, "product is not managed by this manager")

    decision = body.decision
    if decision == "unlock":
        product.status = "active"
        product.buyer_tip = None
        if seller.banned:
            seller.banned = False  # manager overrides an agent ban
    elif decision == "confirm_lock":
        pass  # keep current locked/suspended status; just record the human sign-off
    elif decision == "delete":
        product.status = "delisted"
    else:
        raise HTTPException(400, "decision must be unlock | confirm_lock | delete")

    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=product.id,
        action=f"manager_{decision}",
        evidence_json={"manager_id": manager_id, "decision": decision},
        seller_approved=True,
        created_at=datetime.utcnow(),
    ))
    db.commit()
    return {"product_id": product.id, "new_status": product.status, "decision": decision}

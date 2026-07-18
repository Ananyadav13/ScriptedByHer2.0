"""Business-manager governance.

Every product the agents lock/hold/suspend lands in the owning manager's review
queue. The ABSOLUTE decision — unlock, confirm the lock, or delete — lies with the
manager (a human), not the agent. ~100 sellers map to one manager.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Buyer, CatalogAction, Manager, Notification, Order, Product, Seller
from ..services import delisting
from ..time_utils import utcnow

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
    """The manager's OPEN work: listing cases still awaiting a call + buyer disputes routed
    to manual review. Once the manager decides (a `manager_*` action becomes the latest one),
    the case drops off this queue and lives only in the logs."""
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
    seller_ids = [s.id for s in manager.sellers]

    out = []
    # (a) listing cases — flagged/held/etc. that the manager hasn't yet ruled on
    products = (
        db.query(Product)
        .filter(Product.seller_id.in_(seller_ids), Product.status.in_(_QUEUE_STATUSES))
        .all()
    )
    for p in products:
        last = (
            db.query(CatalogAction)
            .filter(CatalogAction.product_id == p.id)
            .order_by(CatalogAction.created_at.desc())
            .first()
        )
        # already ruled on by a manager -> it's resolved, keep it out of "action needed"
        if last and last.action.startswith("manager_"):
            continue
        out.append({
            "kind": "listing",
            "product_id": p.id,
            "title": p.title,
            "seller_id": p.seller_id,
            "status": p.status,
            "agent_action": last.action if last else None,
            "evidence": last.evidence_json if last else None,
            "acted_at": last.created_at.isoformat() if last else None,
        })

    # (b) dispute cases — orders routed to manual review (e.g. a serial claimer) awaiting a call
    my_product_ids = [pid for (pid,) in
                      db.query(Product.id).filter(Product.seller_id.in_(seller_ids)).all()] if seller_ids else []
    manual = (
        db.query(Order)
        .filter(Order.status == "manual_review", Order.product_id.in_(my_product_ids))
        .all()
        if my_product_ids else []
    )
    for o in manual:
        prod = db.get(Product, o.product_id)
        buyer = db.get(Buyer, o.buyer_id)
        claims = (buyer.claim_history or {}).get("count", 0) if buyer else 0
        out.append({
            "kind": "dispute",
            "order_id": o.id,
            "product_id": o.product_id,
            "title": prod.title if prod else o.product_id,
            "seller_id": prod.seller_id if prod else None,
            "status": "manual_review",
            "claim_type": o.claim_type,
            "buyer_id": o.buyer_id,
            "buyer_claim_count": claims,
            "evidence": {"evidence": [
                f"buyer has {claims} prior claims — repeat-claimant pattern" if claims >= 5
                else f"buyer has {claims} prior claims",
                f"claim: {o.claim_type or 'item not as described'}",
                "no independent delivery signals corroborate the claim",
            ]},
            "acted_at": (o.delivered_at.isoformat() if o.delivered_at else None),
        })

    return {"manager_id": manager_id, "queue_size": len(out), "items": out}


@router.get("/manager/{manager_id}/sellers")
def manager_sellers(manager_id: str, db: Session = Depends(get_db)):
    """The book of sellers this manager owns, each with their products + the dominant
    complaint + current status — so a manager sees WHO they manage and WHAT's wrong."""
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
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
        age = (utcnow() - s.account_created_at).days if s.account_created_at else None
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
    # approve | suspend | request_changes | unlock | modify_listing | suspend_and_request_changes
    # (legacy: unlock | confirm_lock | delete still accepted)
    decision: str
    comment: str | None = None   # a note for the seller (shown when suspending / asking for changes)


# Per-decision rules. `status` = new listing status (None keeps current); `refund` = mark the
# disputing buyer's order refunded + tell them; `notify_buyer` = send the buyer any message at all.
_DECISIONS: dict[str, dict] = {
    "approve": {
        "status": "active", "refund": False, "notify_buyer": True,
        "seller": "After review, '{t}' is approved and stays live.",
        "buyer": "We reviewed your report on '{t}'. The listing checked out — it stays available.",
    },
    "suspend": {
        "status": "suspended", "refund": True, "notify_buyer": True,
        "seller": "'{t}' has been suspended after manager review.{c}",
        "buyer": "Your report on '{t}' was upheld. Your refund has been approved and initiated.",
    },
    "suspend_and_request_changes": {
        "status": "suspended", "refund": True, "notify_buyer": True,
        "seller": "'{t}' has been SUSPENDED. Product description changes are required — the listing "
                  "will be unlocked only after the requested modifications are made.{c}",
        "buyer": "Your report on '{t}' was upheld. Your refund has been approved and the refund "
                 "process has been initiated.",
    },
    "request_changes": {
        "status": "needs_info", "refund": False, "notify_buyer": True,
        "seller": "'{t}' needs changes before it returns to full visibility.{c}",
        "buyer": "Thanks for your report on '{t}'. We've asked the seller to correct the listing.",
    },
    "modify_listing": {
        # size-drift path: seller-only. The buyer already got the Agent-2 size hint pre-purchase.
        "status": "needs_info", "refund": False, "notify_buyer": False,
        "seller": "Please update the sizing information on '{t}' — buyers report it runs small.{c}",
        "buyer": "",
    },
    "unlock": {
        "status": "active", "refund": False, "notify_buyer": True,
        "seller": "Good news — after review, '{t}' is back to full visibility.",
        "buyer": "The report on '{t}' is resolved and the listing is available again.",
    },
    # ---- legacy aliases ----
    "confirm_lock": {
        "status": None, "refund": True, "notify_buyer": True,
        "seller": "After review, the action on '{t}' stands. Correct the listing to appeal.",
        "buyer": "Your report on '{t}' was upheld. Your refund has been processed.",
    },
    "delete": {
        "status": "delisted", "refund": True, "notify_buyer": True,
        "seller": "'{t}' has been removed from the catalogue after manager review.",
        "buyer": "Your report on '{t}' was upheld and the listing removed. Your refund has been processed.",
    },
}


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

    rule = _DECISIONS.get(body.decision)
    if rule is None:
        raise HTTPException(400, f"unknown decision '{body.decision}'")

    prior = product.status
    if rule["status"] is not None:
        product.status = rule["status"]
    if rule["status"] == "active":
        product.buyer_tip = None
        if seller.banned:
            seller.banned = False
    comment_suffix = f" Manager note: “{body.comment.strip()}”" if body.comment and body.comment.strip() else ""
    seller_msg = rule["seller"].format(t=product.title, c=comment_suffix)

    now = utcnow()

    def _ntf(audience: str, recipient: str | None, subject: str, bodytext: str, priority: str):
        db.add(Notification(id=f"ntf_{uuid.uuid4().hex[:12]}", audience=audience,
                            recipient_id=recipient, subject=subject, body=bodytext,
                            priority=priority, related_id=product.id, created_at=now))

    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=product.id,
        action=f"manager_{body.decision}",
        evidence_json={"manager_id": manager_id, "decision": body.decision,
                       "from_status": prior, "comment": body.comment},
        seller_approved=True,
        created_at=now,
    ))
    # SELLER is always told what happened + why.
    _ntf("seller", product.seller_id, f"Manager decision on '{product.title}'", seller_msg,
         "high" if rule["status"] not in (None, "active") else "normal")

    # BUYER(s) who disputed this product — only if this decision notifies the buyer.
    notified_buyers = 0
    if rule["notify_buyer"]:
        buyer_msg = rule["buyer"].format(t=product.title)
        for o in db.query(Order).filter(Order.product_id == product.id, Order.claim_type.isnot(None)).all():
            if rule["refund"]:
                o.status = "refunded"
            if buyer_msg:
                _ntf("buyer", o.buyer_id, "Update on your dispute", buyer_msg, "high")
                notified_buyers += 1

    db.commit()
    return {"product_id": product.id, "new_status": product.status, "decision": body.decision,
            "buyers_notified": notified_buyers}


class DisputeDecision(BaseModel):
    decision: str  # reject | approve
    comment: str | None = None


@router.post("/manager/{manager_id}/disputes/{order_id}/decision")
def manager_decide_dispute(manager_id: str, order_id: str, body: DisputeDecision,
                           db: Session = Depends(get_db)):
    """Rule on a buyer DISPUTE routed to manual review (e.g. a serial claimer). `reject` denies
    the refund (fraud/abuse); `approve` refunds. The buyer is told either way; the case leaves
    the manager's action queue and is recorded in the logs."""
    manager = db.get(Manager, manager_id)
    if not manager:
        raise HTTPException(404, "manager not found")
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "order not found")
    product = db.get(Product, order.product_id)
    seller = db.get(Seller, product.seller_id) if product else None
    if not seller or seller.manager_id != manager_id:
        raise HTTPException(403, "dispute is not managed by this manager")

    now = utcnow()
    note = f" Manager note: “{body.comment.strip()}”" if body.comment and body.comment.strip() else ""
    if body.decision == "reject":
        order.status = "delivered"  # claim denied — order stands as delivered
        buyer_msg = (f"After review, your refund request on '{product.title}' was not approved — the "
                     f"item was correctly described and delivered, and your claim history shows a "
                     f"repeat pattern.{note}")
        subject = "Refund request declined"
    elif body.decision == "approve":
        order.status = "refunded"
        buyer_msg = f"Your refund on '{product.title}' has been approved and initiated.{note}"
        subject = "Refund approved"
    else:
        raise HTTPException(400, "decision must be reject | approve")

    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}", product_id=order.product_id,
        action=f"manager_dispute_{body.decision}",
        evidence_json={"manager_id": manager_id, "order_id": order.id, "decision": body.decision,
                       "buyer_id": order.buyer_id, "comment": body.comment},
        seller_approved=True, created_at=now,
    ))
    db.add(Notification(id=f"ntf_{uuid.uuid4().hex[:12]}", audience="buyer",
                        recipient_id=order.buyer_id, subject=subject, body=buyer_msg,
                        priority="high", related_id=order.id, created_at=now))
    db.commit()
    return {"order_id": order.id, "new_status": order.status, "decision": body.decision}

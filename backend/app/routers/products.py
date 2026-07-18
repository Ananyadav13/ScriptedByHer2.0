"""Product catalog API + listing-lock consequences."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CatalogAction, Product
from ..schemas import ProductDetail, ProductOut
from ..time_utils import utcnow

router = APIRouter(prefix="/products", tags=["products"])

# statuses where a buyer/seller should see WHY the listing is restricted.
# NOTE: `flagged` is deliberately NOT here — it's an advisory manager recommendation,
# the sale continues with no buyer-facing restriction.
# `correction_window` (Agent 2 audit) IS shown: the buyer sees the listing is being
# corrected (a heads-up), and the reason carries the dominant complaint.
_RESTRICTED = {"locked", "on_hold", "needs_info", "suspended", "correction_window"}


def _latest_action(db: Session, product_id: str) -> CatalogAction | None:
    return (
        db.query(CatalogAction)
        .filter(CatalogAction.product_id == product_id)
        .order_by(CatalogAction.created_at.desc())
        .first()
    )


def _latest_decision_action(db: Session, product_id: str) -> CatalogAction | None:
    """The most recent action that carries a status DECISION (skips bookkeeping rows like
    `fix_draft`/`reverify`/`manager_*` that can be newer but hold no lock reason)."""
    rows = (
        db.query(CatalogAction)
        .filter(CatalogAction.product_id == product_id)
        .order_by(CatalogAction.created_at.desc())
        .limit(20)
        .all()
    )
    for a in rows:
        if (a.evidence_json or {}).get("decision"):
            return a
    return rows[0] if rows else None


def _rating(p: Product) -> tuple[float, int, int]:
    """(avg, ratings_total, review_count). `ratings_total` counts rating-only submissions
    too (real listings have ~3x more ratings than written reviews); it falls back to the
    review count when unseeded. The average is always over the reviews we actually hold."""
    revs = p.reviews or []
    n = len(revs)
    if not n:
        return 0.0, p.ratings_total or 0, 0
    avg = round(sum(r.rating for r in revs) / n, 1)
    return avg, (p.ratings_total or n), n


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    out = []
    for p in db.query(Product).all():
        dto = ProductOut.model_validate(p)
        dto.rating, dto.rating_count, dto.review_count = _rating(p)
        out.append(dto)
    return out


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "product not found")

    detail = ProductDetail.model_validate(p)
    detail.rating, detail.rating_count, detail.review_count = _rating(p)
    detail.qc_requested = p.qc_requested_at is not None and not p.qc_responded
    if p.status in _RESTRICTED:
        last = _latest_decision_action(db, product_id)
        if last is not None:
            detail.latest_action = last.action
            ev = last.evidence_json or {}
            # evidence_json carries the verdict decision + evidence list
            reason = ev.get("decision")
            evidence = ev.get("evidence")
            if evidence:
                reason = f"{reason}: {'; '.join(evidence)}" if reason else "; ".join(evidence)
            detail.lock_reason = reason
    return detail


@router.post("/{product_id}/reverify")
def reverify(product_id: str, db: Session = Depends(get_db)):
    """Seller 'live photo' reverification stub: a locked/held listing goes back to
    active and the quality-check clock is cleared. Logged in catalog_actions.
    (In production this would gate on an actual uploaded live photo / QC video.)"""
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "product not found")
    if p.status not in _RESTRICTED:
        raise HTTPException(400, f"product is {p.status}, nothing to reverify")

    prior = p.status
    p.status = "active"
    p.qc_responded = True
    p.buyer_tip = None
    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=p.id,
        action="reverify",
        evidence_json={"from_status": prior, "note": "seller reverification accepted"},
        seller_approved=True,
        created_at=utcnow(),
    ))
    db.commit()
    return {"product_id": p.id, "new_status": p.status, "from_status": prior}

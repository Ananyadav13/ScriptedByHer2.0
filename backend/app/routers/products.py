"""Product catalog API + listing-lock consequences (Phase 3)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CatalogAction, Product
from ..schemas import ProductDetail, ProductOut

router = APIRouter(prefix="/products", tags=["products"])

# statuses where a buyer/seller should see WHY the listing is restricted
_RESTRICTED = {"locked", "on_hold", "needs_info", "suspended"}


def _latest_action(db: Session, product_id: str) -> CatalogAction | None:
    return (
        db.query(CatalogAction)
        .filter(CatalogAction.product_id == product_id)
        .order_by(CatalogAction.created_at.desc())
        .first()
    )


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "product not found")

    detail = ProductDetail.model_validate(p)
    detail.qc_requested = p.qc_requested_at is not None and not p.qc_responded
    if p.status in _RESTRICTED:
        last = _latest_action(db, product_id)
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
        created_at=datetime.utcnow(),
    ))
    db.commit()
    return {"product_id": p.id, "new_status": p.status, "from_status": prior}

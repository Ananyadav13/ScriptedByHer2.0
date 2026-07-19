"""Product catalog API + listing-lock consequences."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..logging_config import log_moderation_event
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


# The ONLY status a seller may clear themselves. `needs_info` means the agent asked for a
# quality-check video and is waiting (see rules.SELLER_QC_SLA_DAYS) — responding to that
# request is the seller's documented move, so it restores the listing without a manager.
#
# Every other restricted status is a MANAGER decision (`locked`, `suspended`, `on_hold`,
# `correction_window`). Letting a seller clear those would make the system's central
# guarantee — agents recommend, managers decide — untrue: a listing suspended for fraud
# could be self-restored with one unauthenticated request. Those return 409 and point the
# caller at the manager route instead.
_SELLER_CLEARABLE = {"needs_info"}
_MANAGER_OWNED = _RESTRICTED - _SELLER_CLEARABLE


@router.post("/{product_id}/reverify")
def reverify(product_id: str, db: Session = Depends(get_db)):
    """Seller responds to a quality-check request: `needs_info` -> `active`.

    This is the seller's half of the QC-video loop, not a general unlock. A manager-owned
    status is refused (409) — only the owning manager can reverse their own decision, via
    POST /manager/{manager_id}/products/{product_id}/decision.

    Idempotent: re-posting once the listing is already active is a no-op that returns the
    same body rather than writing a second audit row.
    """
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "product not found")

    if p.status in _MANAGER_OWNED:
        raise HTTPException(
            409,
            f"'{p.status}' is a manager decision and cannot be cleared by reverification — "
            f"use POST /manager/{{manager_id}}/products/{product_id}/decision",
        )
    if p.status not in _SELLER_CLEARABLE:
        # already active (or some other unrestricted state): nothing to do, and saying so
        # with 200 keeps a retried request from looking like a failure.
        return {"product_id": p.id, "new_status": p.status, "from_status": p.status,
                "applied": False, "detail": "no quality-check request is open"}

    prior = p.status
    p.status = "active"
    p.qc_responded = True
    p.buyer_tip = None
    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=p.id,
        action="reverify",
        evidence_json={"from_status": prior, "note": "seller responded to the quality-check request"},
        seller_approved=True,
        created_at=utcnow(),
    ))
    db.commit()
    log_moderation_event("seller", "reverify", p.id, from_status=prior, to_status=p.status)
    return {"product_id": p.id, "new_status": p.status, "from_status": prior, "applied": True}

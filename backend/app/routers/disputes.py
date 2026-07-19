"""Post-delivery dispute API.

A dispute is an investigation with trigger `post_delivery` keyed on an ORDER. The
orchestrator corroborates delivery signals (OTP-vs-items, hub anomaly, missing
geo-photo): two independent signals -> refund_fast_track; a serial-claimer history
-> manual_review; a fraudulent hub -> immediate ops escalation. Same SSE trace and
`GET /investigations/{id}` surface as a product investigation — the frontend reuses
the trace panel wholesale.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import events
from ..agents.orchestrator import run_investigation
from ..db import get_db
from ..models import Investigation, Order
from ..time_utils import utcnow

router = APIRouter(tags=["disputes"])


# The claim categories a buyer may file — mirrors `frontend/src/lib/orders.ts`. Kept here
# rather than in services/rules.py because this is an API-contract enum, not a tunable
# decision threshold. `wrong_colour` is colour-sensitive (see rules.COLOUR_SENSITIVE_CLAIMS).
CLAIM_TYPES = frozenset({
    "item_not_as_described", "fabric_mismatch", "damaged", "not_received", "wrong_colour",
})

# A dispute may only be opened on an order that is still open. `refunded` is terminal and
# `manual_review` already has a case in front of a manager — reopening either would let a
# buyer file the same claim repeatedly and spawn an agent run each time.
DISPUTABLE_STATUSES = frozenset({"delivered"})


class DisputeIn(BaseModel):
    order_id: str
    claim_type: str = "item_not_as_described"
    evidence_paths: list[str] = []              # buyer media (photos OR videos) for this claim


@router.post("/dispute")
def open_dispute(body: DisputeIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "order not found")
    if body.claim_type not in CLAIM_TYPES:
        raise HTTPException(422, f"claim_type must be one of {sorted(CLAIM_TYPES)}")
    if order.status not in DISPUTABLE_STATUSES:
        # matches the `dispute_available` flag the buyer's My Orders view already renders,
        # so the UI and the API can never disagree about what is disputable.
        raise HTTPException(409, f"order is '{order.status}' — no dispute can be opened on it")

    # One open investigation per order. Without this a double-clicked button starts two
    # agent loops racing on the same order, burning quota and duplicating outcomes.
    existing = (
        db.query(Investigation)
        .filter(Investigation.order_id == order.id,
                Investigation.status.in_(("queued", "running")))
        .first()
    )
    if existing is not None:
        raise HTTPException(
            409,
            f"an investigation ({existing.id}) is already running on this order",
        )

    # attach buyer evidence + the claim so check_media_evidence can compare against the
    # product's quality fingerprint (and know whether COLOUR is in scope for this claim)
    if body.evidence_paths:
        order.buyer_evidence_json = list(body.evidence_paths)
    order.claim_type = body.claim_type
    db.commit()

    inv_id = f"inv_{uuid.uuid4().hex[:12]}"
    db.add(Investigation(
        id=inv_id,
        product_id=order.product_id,
        order_id=order.id,
        trigger="post_delivery",
        status="queued",
        tool_calls_log_json=[],
        created_at=utcnow(),
    ))
    db.commit()

    # Create the event queue BEFORE the task starts so an SSE client that connects
    # immediately never misses the opening events (same pattern as /investigate).
    events.create(inv_id)
    background.add_task(run_investigation, inv_id, None, "post_delivery",
                       order.id, body.claim_type)
    return {"investigation_id": inv_id, "status": "queued", "order_id": order.id}

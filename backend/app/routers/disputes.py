"""Post-delivery dispute API (Phase 3).

A dispute is an investigation with trigger `post_delivery` keyed on an ORDER. The
orchestrator corroborates delivery signals (OTP-vs-items, hub anomaly, missing
geo-photo): two independent signals -> refund_fast_track; a serial-claimer history
-> manual_review; a fraudulent hub -> immediate ops escalation. Same SSE trace and
`GET /investigations/{id}` surface as a product investigation — the frontend reuses
the trace panel wholesale.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import events
from ..agents.orchestrator import run_investigation
from ..db import get_db
from ..models import Investigation, Order

router = APIRouter(tags=["disputes"])


class DisputeIn(BaseModel):
    order_id: str
    claim_type: str = "item_not_as_described"   # free-form buyer claim category
    evidence_paths: list[str] = []              # buyer media (photos OR videos) for this claim


@router.post("/dispute")
def open_dispute(body: DisputeIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "order not found")

    # attach buyer evidence so check_media_evidence can compare it to the listing video
    if body.evidence_paths:
        order.buyer_evidence_json = list(body.evidence_paths)
        db.commit()

    inv_id = f"inv_{uuid.uuid4().hex[:12]}"
    db.add(Investigation(
        id=inv_id,
        product_id=order.product_id,
        order_id=order.id,
        trigger="post_delivery",
        status="queued",
        tool_calls_log_json=[],
        created_at=datetime.utcnow(),
    ))
    db.commit()

    # Create the event queue BEFORE the task starts so an SSE client that connects
    # immediately never misses the opening events (same pattern as /investigate).
    events.create(inv_id)
    background.add_task(run_investigation, inv_id, None, "post_delivery",
                       order.id, body.claim_type)
    return {"investigation_id": inv_id, "status": "queued", "order_id": order.id}

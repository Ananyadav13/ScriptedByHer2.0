"""Investigation API: kick off Agent 1, read status/log/verdict."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agents import events
from ..agents.orchestrator import run_investigation
from ..db import get_db
from ..models import Investigation

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

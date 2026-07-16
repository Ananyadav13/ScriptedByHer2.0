"""Ops/support surface: notification inbox + hub health (feeds the admin UI in Phase 5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Hub, Notification

router = APIRouter(tags=["ops"])


@router.get("/notifications")
def list_notifications(audience: str | None = None, recipient_id: str | None = None,
                       db: Session = Depends(get_db)):
    q = db.query(Notification)
    if audience:
        q = q.filter(Notification.audience == audience)
    if recipient_id:
        q = q.filter(Notification.recipient_id == recipient_id)
    rows = q.order_by(Notification.created_at.desc()).all()
    return [
        {
            "id": n.id, "audience": n.audience, "recipient_id": n.recipient_id,
            "subject": n.subject, "body": n.body,
            "priority": n.priority, "related_id": n.related_id,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.get("/hubs")
def list_hubs(db: Session = Depends(get_db)):
    rows = db.query(Hub).order_by(Hub.case_count.desc()).all()  # worst offenders first
    return [
        {"id": h.id, "name": h.name, "region": h.region,
         "score": h.score, "case_count": h.case_count}
        for h in rows
    ]

"""Idempotent writes for the audit trail and the outbound notification queue.

THE PROBLEM
-----------
Agent runs are re-triggerable by design: a buyer can re-open a product page, a manager can
re-run the catalog audit, a tripwire can fire twice, and two investigations can execute
concurrently in background threads. Every one of those paths writes `CatalogAction` and
`Notification` rows. With random primary keys, each repeat produced a fresh duplicate — so
the manager's log showed the same lock three times and the seller got three identical
emails about it. The audit trail is a headline claim of this project; a trail that
double-counts is worse than none.

WHY NOT "CHECK, THEN INSERT"
----------------------------
Because it loses the race. Two threads both query "does this row exist?", both see no, both
insert. Measured: 12 threads released from a barrier produced 12 duplicate rows through
exactly that window.

THE APPROACH
------------
Derive the primary key from the event's IDENTITY — what happened, to what, in which case —
instead of from randomness. A duplicate then collides on the PRIMARY KEY, which the
database rejects however the threads interleave. `insert_once` performs the insert inside a
SAVEPOINT so the collision rolls back that one statement without discarding the status
changes the caller has already staged.

CASE SCOPING
------------
Dedupe is scoped to the current *case*, not to all history. Re-running an investigation
that reaches the same conclusion must not write a second lock — but once a manager has
ruled, that case is closed, and a later re-offence is a genuinely new event that must be
recorded. `case_epoch` draws that line at the most recent `manager_*` action.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import CatalogAction, Notification
from .time_utils import utcnow


def case_epoch(db: Session, related_id: str | None) -> datetime | None:
    """When the current case on `related_id` opened — the last time a manager ruled.

    None means the manager has never ruled on it, in which case dedupe considers all
    history for that entity.
    """
    if not related_id:
        return None
    row = (
        db.query(CatalogAction)
        .filter(CatalogAction.product_id == related_id,
                CatalogAction.action.startswith("manager_"))
        .order_by(CatalogAction.created_at.desc())
        .first()
    )
    return row.created_at if row else None


def case_key(prefix: str, epoch: datetime | None, *parts: str | None) -> str:
    """A primary key derived from the event's identity rather than randomness."""
    seed = "|".join([prefix, *(p or "" for p in parts), epoch.isoformat() if epoch else "-"])
    return f"{prefix}_{hashlib.sha1(seed.encode()).hexdigest()[:16]}"


def insert_once(db: Session, row) -> bool:
    """Insert `row`; return False if its primary key already exists.

    The SAVEPOINT is what makes this safe to call mid-transaction: a bare IntegrityError
    would poison the session and discard everything staged alongside it.
    """
    try:
        with db.begin_nested():
            db.add(row)
        return True
    except IntegrityError:
        return False


def log_action_once(db: Session, product_id: str, action: str, evidence: dict,
                    seller_approved: bool = False) -> bool:
    """Record one catalog action, at most once per (product, action, case)."""
    return insert_once(db, CatalogAction(
        id=case_key("act", case_epoch(db, product_id), product_id, action),
        product_id=product_id,
        action=action,
        evidence_json=evidence,
        seller_approved=seller_approved,
        created_at=utcnow(),
    ))


def notify_once(db: Session, audience: str, subject: str, body: str,
                priority: str = "normal", related_id: str | None = None,
                recipient_id: str | None = None) -> bool:
    """Queue an outbound message, at most once per (audience, subject, case).

    Dedupe is the default rather than opt-in because no caller ever wants to send the same
    person the same message about the same case twice.
    """
    return insert_once(db, Notification(
        id=case_key("ntf", case_epoch(db, related_id), audience, subject, related_id),
        audience=audience, recipient_id=recipient_id, subject=subject, body=body,
        priority=priority, related_id=related_id, created_at=utcnow(),
    ))

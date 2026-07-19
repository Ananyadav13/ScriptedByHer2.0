"""Regression tests for state integrity: idempotency, validation, and governance.

Every test here corresponds to a defect found by adversarial probing of a running server.
They are written to FAIL if the guard is removed, so the bug cannot come back quietly.

Grouped by the invariant each one protects:
  1. Idempotent writes      — repeating an action must not duplicate its effects
  2. Endpoint validation    — unknown ids and bad enums are refused, not queued
  3. Legal state transitions— terminal states stay terminal
  4. Governance             — a manager decision cannot be bypassed
"""
from __future__ import annotations

import threading

import pytest

from app.db import SessionLocal
from app.models import CatalogAction, Notification, Order, Product
from app.schemas import Verdict


def _verdict(decision="counterfeit_lock", action="lock"):
    return Verdict(decision=decision, confidence=0.9, evidence=["seeded evidence"],
                   action=action, buyer_explanation="explained to the buyer")


def _count_actions(db, product_id: str, action: str) -> int:
    return (db.query(CatalogAction)
            .filter(CatalogAction.product_id == product_id, CatalogAction.action == action)
            .count())


# ---------------------------------------------------------------------------
# 1. Idempotent writes
# ---------------------------------------------------------------------------
class TestIdempotency:
    """Repeating an action must not duplicate audit rows or notifications.

    The audit trail is a headline claim of this project. A trail that double-counts a
    lock — because a button was double-clicked or two investigations raced — is worse
    than no trail, because it is confidently wrong.
    """

    def test_repeated_execution_writes_one_action(self, seeded_db):
        from app.agents import orchestrator
        pid = "prod_counterfeit_rolex"
        product = seeded_db.get(Product, pid)

        for _ in range(5):
            orchestrator._execute_action(seeded_db, product, None, _verdict())
        seeded_db.commit()

        assert _count_actions(seeded_db, pid, "lock") == 1

    def test_concurrent_execution_writes_one_action(self):
        """The check-then-insert version of this lost the race: 12 threads released from
        a barrier produced 12 duplicate rows. Deterministic primary keys close it."""
        from app.agents import orchestrator
        from app.seed import reset_and_seed
        reset_and_seed()

        pid = "prod_counterfeit_rolex"
        n = 12
        barrier = threading.Barrier(n)
        errors: list[str] = []

        def worker():
            try:
                db = SessionLocal()
                product = db.get(Product, pid)
                barrier.wait(timeout=10)      # maximise overlap
                orchestrator._execute_action(db, product, None, _verdict())
                db.commit()
                db.close()
            except Exception as exc:          # noqa: BLE001 — surfaced in the assert below
                errors.append(f"{type(exc).__name__}: {exc}")

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"concurrent execution raised: {errors}"
        db = SessionLocal()
        try:
            assert _count_actions(db, pid, "lock") == 1
        finally:
            db.close()

    def test_repeated_execution_sends_one_notification(self, seeded_db):
        from app.agents import orchestrator
        pid = "prod_counterfeit_rolex"
        product = seeded_db.get(Product, pid)
        subject = "Listing locked: counterfeit"

        for _ in range(4):
            orchestrator._execute_action(seeded_db, product, None, _verdict())
        seeded_db.commit()

        sent = (seeded_db.query(Notification)
                .filter(Notification.related_id == pid, Notification.subject == subject)
                .count())
        assert sent == 1

    def test_manager_decision_opens_a_new_case(self, seeded_db):
        """Dedupe is scoped to the current case, not all history.

        Suppressing forever would be its own bug: a product that re-offends after a
        manager cleared it must be recorded again, or the agent looks asleep.
        """
        from app.agents import orchestrator
        from app.idempotency import log_action_once
        from app.time_utils import utcnow

        pid = "prod_counterfeit_rolex"
        product = seeded_db.get(Product, pid)

        orchestrator._execute_action(seeded_db, product, None, _verdict())
        orchestrator._execute_action(seeded_db, product, None, _verdict())
        seeded_db.commit()
        assert _count_actions(seeded_db, pid, "lock") == 1

        # a manager rules -> the case closes
        seeded_db.add(CatalogAction(
            id="act_manager_ruling_test", product_id=pid, action="manager_approve",
            evidence_json={}, created_at=utcnow(),
        ))
        seeded_db.commit()

        # the product re-offends: this is a NEW event and must be recorded
        orchestrator._execute_action(seeded_db, product, None, _verdict())
        seeded_db.commit()
        assert _count_actions(seeded_db, pid, "lock") == 2

    def test_repeated_audit_does_not_grow_the_audit_log(self, client):
        """`logistics_referral` does not change product status (a delivery fault is the
        hub's problem and the listing stays live), so it stayed in the sweep's query set
        and re-logged itself on every run. Verified before the fix: 9 -> 10 -> 11 -> 12.
        """
        def totals():
            db = SessionLocal()
            try:
                return db.query(CatalogAction).count(), db.query(Notification).count()
            finally:
                db.close()

        assert client.post("/audit", json={"cluster": False}).status_code == 200
        after_first = totals()

        for _ in range(3):
            client.post("/audit", json={"cluster": False})

        assert totals() == after_first, "a repeated audit wrote new rows"


# ---------------------------------------------------------------------------
# 2. Endpoint validation
# ---------------------------------------------------------------------------
class TestEndpointValidation:
    """Unknown ids and invalid enums are refused up front.

    These used to return 200 and queue work that could only fail later in a background
    thread, where the caller never sees the error.
    """

    def test_investigate_rejects_unknown_product(self, client):
        r = client.post("/investigate", json={"product_id": "prod_does_not_exist"})
        assert r.status_code == 404

    def test_investigate_rejects_unknown_order(self, client):
        r = client.post("/investigate", json={"order_id": "order_does_not_exist"})
        assert r.status_code == 404

    def test_investigate_rejects_unknown_trigger(self, client):
        pid = client.get("/products").json()[0]["id"]
        r = client.post("/investigate", json={"product_id": pid, "trigger": "not_a_trigger"})
        assert r.status_code == 422

    def test_investigate_requires_an_identifier(self, client):
        assert client.post("/investigate", json={}).status_code == 400

    def test_dispute_rejects_unknown_order(self, client):
        r = client.post("/dispute", json={"order_id": "order_nope", "claim_type": "damaged"})
        assert r.status_code == 404

    def test_dispute_rejects_unknown_claim_type(self, client):
        buyers = client.get("/buyers").json()
        orders = client.get(f"/buyers/{buyers[0]['id']}/orders").json()["orders"]
        order = next(o for o in orders if o["dispute_available"])
        r = client.post("/dispute", json={"order_id": order["id"], "claim_type": "not_a_claim"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 3. Legal state transitions
# ---------------------------------------------------------------------------
class TestStateTransitions:
    def test_only_one_investigation_runs_per_order(self, client):
        """A double-clicked dispute button used to start two agent loops on one order —
        two LLM runs racing to write the same outcome."""
        buyers = client.get("/buyers").json()
        orders = client.get(f"/buyers/{buyers[0]['id']}/orders").json()["orders"]
        order = next(o for o in orders if o["dispute_available"])

        first = client.post("/dispute", json={"order_id": order["id"],
                                              "claim_type": "fabric_mismatch"})
        assert first.status_code == 200

        second = client.post("/dispute", json={"order_id": order["id"],
                                               "claim_type": "fabric_mismatch"})
        assert second.status_code == 409

    def test_no_dispute_on_a_settled_order(self, client):
        """`refunded` is terminal. The buyer's My Orders view already hides the button;
        the API must agree, or the two can disagree about what is disputable."""
        buyers = client.get("/buyers").json()
        orders = client.get(f"/buyers/{buyers[0]['id']}/orders").json()["orders"]
        target = orders[0]["id"]

        db = SessionLocal()
        try:
            db.get(Order, target).status = "refunded"
            db.commit()
        finally:
            db.close()

        r = client.post("/dispute", json={"order_id": target, "claim_type": "damaged"})
        assert r.status_code == 409

    def test_refunded_order_is_never_refunded_twice(self, seeded_db):
        """Wired to a real payment provider, a repeat would be a second disbursement."""
        from app.agents import orchestrator
        order = seeded_db.query(Order).filter(Order.status == "delivered").first()
        product = seeded_db.get(Product, order.product_id)

        v = _verdict(decision="refund_fast_track", action="refund")
        orchestrator._execute_action(seeded_db, product, order.id, v)
        seeded_db.commit()
        assert order.status == "refunded"

        # a second run must not re-notify or re-settle
        orchestrator._execute_action(seeded_db, product, order.id, v)
        seeded_db.commit()
        refund_notes = (seeded_db.query(Notification)
                        .filter(Notification.related_id == order.id)
                        .count())
        assert order.status == "refunded"
        assert refund_notes == 1


# ---------------------------------------------------------------------------
# 4. Governance
# ---------------------------------------------------------------------------
class TestGovernance:
    """"Agents recommend, managers decide" has to be enforced, not just documented.

    `POST /products/{id}/reverify` previously restored ANY restricted listing — including
    one suspended for fraud — from an unauthenticated, empty request. That made the
    project's central guarantee untrue.
    """

    @pytest.mark.parametrize("status", ["suspended", "locked", "on_hold", "correction_window"])
    def test_reverify_cannot_clear_a_manager_owned_status(self, client, status):
        pid = "prod_normal_mug"
        db = SessionLocal()
        try:
            db.get(Product, pid).status = status
            db.commit()
        finally:
            db.close()

        r = client.post(f"/products/{pid}/reverify")
        assert r.status_code == 409, f"'{status}' must not be seller-clearable"

        db = SessionLocal()
        try:
            assert db.get(Product, pid).status == status, "status changed despite the refusal"
        finally:
            db.close()

    def test_reverify_clears_needs_info(self, client):
        """The legitimate half of the QC loop still works: a seller responding to a
        quality-check request restores their own listing."""
        pid = "prod_normal_mug"
        db = SessionLocal()
        try:
            db.get(Product, pid).status = "needs_info"
            db.commit()
        finally:
            db.close()

        r = client.post(f"/products/{pid}/reverify")
        assert r.status_code == 200
        assert r.json()["new_status"] == "active"
        assert r.json()["applied"] is True

    def test_reverify_is_idempotent(self, client):
        # A product no other test in this module touches: the `client` fixture is
        # module-scoped, so sharing one would count another test's audit row.
        pid = "prod_gadget_earphones"
        db = SessionLocal()
        try:
            db.get(Product, pid).status = "needs_info"
            db.commit()
        finally:
            db.close()

        client.post(f"/products/{pid}/reverify")
        second = client.post(f"/products/{pid}/reverify")
        assert second.status_code == 200
        assert second.json()["applied"] is False

        db = SessionLocal()
        try:
            assert _count_actions(db, pid, "reverify") == 1
        finally:
            db.close()

    def test_reverify_unknown_product_is_404(self, client):
        assert client.post("/products/prod_nope/reverify").status_code == 404

    def test_manager_cannot_act_outside_their_book(self, client):
        """Already covered by the smoke suite; asserted here too because it is the other
        half of the same guarantee."""
        managers = client.get("/managers").json()
        owner = next(m for m in managers
                     if client.get(f"/manager/{m['id']}/queue").json()["items"])
        item = client.get(f"/manager/{owner['id']}/queue").json()["items"][0]
        other = next(m for m in managers if m["id"] != owner["id"])

        r = client.post(f"/manager/{other['id']}/products/{item['product_id']}/decision",
                        json={"decision": "approve"})
        assert r.status_code == 403

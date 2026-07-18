"""Agent 1 orchestration — the investigation loop.

Gemini pivot (14 Jul 2026): a MANUAL function-calling loop over `google-genai`
(not automatic function calling) so every tool call streams to the SSE trace as
it happens. Verdict is a structured `response_schema` call. The verdict's action
is EXECUTED (locks the listing / writes a catalog_action) — the agent acts, it
doesn't just flag.
"""
from __future__ import annotations

import logging
import uuid

from google.genai import types

from ..config import settings
from ..db import SessionLocal
from ..logging_config import log_moderation_event
from ..models import CatalogAction, Hub, Investigation, Notification, Order, Product
from ..schemas import Verdict
from ..services import risk_checks, rules
from ..time_utils import utcnow
from . import agent1_tools, events
from .gemini_client import generate_with_retry
from .prompts import AGENT1_SYSTEM_PROMPT, VERDICT_INSTRUCTION

log = logging.getLogger(__name__)

MAX_TOOL_STEPS = 8


def _investigation_request(product: Product | None, trigger: str, order_id: str | None,
                           claim_type: str | None = None) -> str:
    lines = [f"Investigation trigger: {trigger}."]
    if product is not None:
        lines.append(
            f"Product under review: id={product.id}, title={product.title!r}, "
            f"brand={product.brand!r}, category={product.category}, "
            f"price={product.price}, mrp={product.mrp}, status={product.status}."
        )
    if order_id:
        lines.append(f"Related order under dispute: {order_id}.")
    if claim_type:
        lines.append(f"Buyer's dispute claim type: {claim_type}.")
    lines.append("Investigate using the tools, then give your conclusion.")
    return "\n".join(lines)


def run_investigation(investigation_id: str, product_id: str | None,
                      trigger: str, order_id: str | None = None,
                      claim_type: str | None = None) -> None:
    """Runs in a BackgroundTask worker thread. Streams events, stores verdict, executes action."""
    db = SessionLocal()
    try:
        inv = db.get(Investigation, investigation_id)
        inv.status = "running"
        db.commit()
        events.publish(investigation_id, {"type": "status", "status": "running"})

        product = db.get(Product, product_id) if product_id else None
        # A dispute is keyed on an ORDER with no product_id — resolve the product from the
        # order so the agent knows the REAL listing (otherwise it invents product ids from
        # the order id, e.g. "prod_fabric_dispute_..."). This also gives _execute_action the
        # right product to act on (flag/hold/etc.).
        if product is None and order_id:
            o = db.get(Order, order_id)
            if o is not None and o.product_id:
                product = db.get(Product, o.product_id)
        config = types.GenerateContentConfig(
            system_instruction=AGENT1_SYSTEM_PROMPT,
            tools=[agent1_tools.TOOL],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        contents = [types.Content(
            role="user",
            parts=[types.Part(text=_investigation_request(product, trigger, order_id, claim_type))],
        )]

        tool_log: list[dict] = []
        for _ in range(MAX_TOOL_STEPS):
            resp = generate_with_retry(model=settings.llm_model,
                                       contents=contents, config=config)
            calls = resp.function_calls or []
            if not calls:
                break
            contents.append(resp.candidates[0].content)
            for fc in calls:
                args = dict(fc.args or {})
                events.publish(investigation_id, {"type": "tool_call", "name": fc.name, "args": args})
                result = agent1_tools.dispatch(fc.name, args, db)
                tool_log.append({"tool": fc.name, "args": args, "result": result})
                events.publish(investigation_id, {"type": "tool_result", "name": fc.name, "result": result})
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=fc.name, response={"result": result})],
                ))

        verdict = _final_verdict(contents)
        inv.tool_calls_log_json = tool_log
        inv.verdict_json = verdict.model_dump()
        _execute_action(db, product, order_id, verdict)
        inv.status = "done"
        db.commit()
        events.publish(investigation_id, {"type": "verdict", **verdict.model_dump()})
    except Exception as exc:  # noqa: BLE001 — surface any failure to the trace
        # exc_info: a failed investigation is the one place the traceback is worth keeping,
        # since the SSE trace only ever carries the stringified message.
        log.error("investigation %s failed: %s", investigation_id, exc, exc_info=True)
        db.rollback()
        inv = db.get(Investigation, investigation_id)
        if inv:
            inv.status = "error"
            inv.verdict_json = {"error": str(exc)}
            db.commit()
        events.publish(investigation_id, {"type": "error", "error": str(exc)})
    finally:
        events.finish(investigation_id)
        db.close()


def _final_verdict(contents: list) -> Verdict:
    """One structured call: force a schema-valid Verdict, higher thinking budget."""
    contents = contents + [types.Content(role="user", parts=[types.Part(text=VERDICT_INSTRUCTION)])]
    resp = generate_with_retry(
        model=settings.llm_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Verdict,
            thinking_config=types.ThinkingConfig(thinking_level="high"),
        ),
    )
    return resp.parsed


def _notify(db, audience: str, subject: str, body: str,
            priority: str = "normal", related_id: str | None = None,
            recipient_id: str | None = None) -> None:
    db.add(Notification(
        id=f"ntf_{uuid.uuid4().hex[:12]}",
        audience=audience, recipient_id=recipient_id, subject=subject, body=body,
        priority=priority, related_id=related_id, created_at=utcnow(),
    ))


def _manager_of(product: Product | None) -> str | None:
    """The business manager who owns this product's seller (for routing to their inbox)."""
    seller = getattr(product, "seller", None) if product else None
    return getattr(seller, "manager_id", None) if seller else None


def _log_action(db, product_id: str, action: str, verdict: Verdict) -> None:
    log_moderation_event(
        "agent1", action, product_id,
        decision=verdict.decision, confidence=round(verdict.confidence, 2),
    )
    evidence = {"decision": verdict.decision, "evidence": verdict.evidence,
                "confidence": verdict.confidence}
    # advisory recommendations carry the manager-facing next step + remedy
    if verdict.recommended_action:
        evidence["recommended_action"] = verdict.recommended_action
    if verdict.suggested_remedy:
        evidence["suggested_remedy"] = verdict.suggested_remedy
    db.add(CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=product_id,
        action=action,
        evidence_json=evidence,
        created_at=utcnow(),
    ))


def _request_qc(db, product: Product, verdict: Verdict, buyer_msg: str) -> None:
    """Reversible ask: request a seller quality-check video and start the SLA clock."""
    product.status = "needs_info"
    product.qc_requested_at = utcnow()
    product.qc_responded = False
    _log_action(db, product.id, "request_qc_video", verdict)
    _notify(db, "seller", f"Quality-check video requested (respond within {rules.SELLER_QC_SLA_DAYS} days)",
            f"{product.title}: authenticity is in question but evidence is not yet conclusive. "
            f"Upload a quality-check video to keep the listing live. {buyer_msg}",
            "high", product.id)


def _execute_action(db, product: Product | None, order_id: str | None, verdict: Verdict) -> None:
    """Execute the graduated action ladder — the agent acts, it doesn't just flag.

    Philosophy: authenticity matters, but NOT at the cost of the buyer/seller
    community. Counterfeits people regret get locked; knockoffs people love get
    relabeled, not banned. A fraudulent hub triggers immediate ops escalation.

    Confidence floor (counterfeit flow step 4): a HARD lock needs >= MIN_ORDERS_FOR_ACTION
    orders of evidence OR an overdue quality-check video. Below that we downgrade a
    `counterfeit_lock` to a reversible `request_qc_video` — never punish on thin data.
    """
    d = verdict.decision
    buyer_msg = verdict.buyer_explanation

    # ---- product-centric outcomes ----
    if product is not None:
        if d == "counterfeit_lock":
            order_count = db.query(Order).filter(Order.product_id == product.id).count()
            floor = risk_checks.order_volume(order_count)
            qc = risk_checks.qc_sla_status(product)
            if floor["meets_confidence_floor"] or qc["qc_overdue"]:
                product.status = "locked"
                _log_action(db, product.id, "lock", verdict)
                _notify(db, "seller", "Listing locked: counterfeit",
                        f"{product.title}: {buyer_msg}", "high", product.id)
            else:
                # hard signal but thin evidence -> reversible QC request, not a lock
                _request_qc(db, product, verdict, buyer_msg)

        elif d == "request_qc_video":
            _request_qc(db, product, verdict, buyer_msg)

        elif d == "recommend_review":
            # ADVISORY: uncertain (media) evidence -> recommend to the manager, do NOT
            # punish. Soft `flagged` status keeps the sale live (no buyer impact); the
            # recommendation + remedy ride in the catalog action for the manager queue.
            product.status = "flagged"
            _log_action(db, product.id, "recommend_review", verdict)
            _notify(db, "support", "Agent recommendation: manager review",
                    f"{product.title}: {verdict.recommended_action or 'review'} — "
                    f"{verdict.suggested_remedy or buyer_msg}", "normal", product.id)

        elif d == "relabel_required":
            # keep it live; ask the seller to relabel honestly as a knockoff
            product.knockoff_flag = True
            product.buyer_tip = buyer_msg  # gentle at-purchase note
            _log_action(db, product.id, "relabel_request", verdict)
            _notify(db, "seller", "Relabel required: sell as knockoff/inspired",
                    f"{product.title}: buyers value this product, but it must be relabeled "
                    f"honestly as a knockoff/inspired item. {buyer_msg}", "normal", product.id)

        elif d == "notify_only":
            # sale continues; surface a soft heads-up to the buyer at add-to-cart
            product.buyer_tip = buyer_msg
            _log_action(db, product.id, "notify", verdict)
            _notify(db, "seller", "Listing inconsistency flagged",
                    f"{product.title}: {buyer_msg}", "normal", product.id)
            _notify(db, "support", "Inconsistency to review (sale continues)",
                    f"{product.title}: {buyer_msg}", "normal", product.id)

        elif d == "hold_pending_fix":
            product.status = "on_hold"
            _log_action(db, product.id, "hold", verdict)
            _notify(db, "seller", "Listing on hold — action needed",
                    f"{product.title}: {buyer_msg}", "high", product.id)

        elif d == "ban":
            product.status = "suspended"
            if product.seller is not None:
                product.seller.banned = True
                for p in product.seller.products:
                    p.status = "suspended"
            _log_action(db, product.id, "ban", verdict)
            _notify(db, "support", "Seller banned (repeat offender)",
                    f"{product.title}: {buyer_msg}", "immediate",
                    product.seller_id if product else None)

    # ---- order / delivery outcomes ----
    order = db.get(Order, order_id) if order_id else None
    if order is not None:
        if d == "refund_fast_track":
            order.status = "refunded"
            _notify(db, "support", "Refund fast-tracked (two corroborating signals)",
                    f"Order {order.id}: {buyer_msg}", "high", order.id)
        elif d == "manual_review":
            order.status = "manual_review"
            _notify(db, "support", "Dispute routed to manual review",
                    f"Order {order.id}: {buyer_msg}", "normal", order.id)
        # immediate hub escalation whenever a fraudulent hub is implicated
        hub = db.get(Hub, order.hub_id) if order.hub_id else None
        if hub is not None and (hub.case_count or 0) >= rules.HUB_ESCALATE_CASE_COUNT:
            _notify(db, "ops", "URGENT: fraudulent delivery hub",
                    f"Hub {hub.name} ({hub.id}) has {hub.case_count} cases — investigate immediately.",
                    "immediate", hub.id)

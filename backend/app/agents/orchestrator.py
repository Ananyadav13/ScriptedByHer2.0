"""Agent 1 orchestration — the investigation loop (Phase 2).

Gemini pivot (14 Jul 2026): a MANUAL function-calling loop over `google-genai`
(not automatic function calling) so every tool call streams to the SSE trace as
it happens. Verdict is a structured `response_schema` call. The verdict's action
is EXECUTED (locks the listing / writes a catalog_action) — the agent acts, it
doesn't just flag.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from google.genai import types

from ..db import SessionLocal
from ..models import CatalogAction, Investigation, Product
from ..schemas import Verdict
from . import agent1_tools, events
from .gemini_client import generate_with_retry
from .prompts import AGENT1_SYSTEM_PROMPT, VERDICT_INSTRUCTION

MAX_TOOL_STEPS = 8


def _investigation_request(product: Product | None, trigger: str, order_id: str | None) -> str:
    lines = [f"Investigation trigger: {trigger}."]
    if product is not None:
        lines.append(
            f"Product under review: id={product.id}, title={product.title!r}, "
            f"brand={product.brand!r}, category={product.category}, "
            f"price={product.price}, mrp={product.mrp}, status={product.status}."
        )
    if order_id:
        lines.append(f"Related order under dispute: {order_id}.")
    lines.append("Investigate using the tools, then give your conclusion.")
    return "\n".join(lines)


def run_investigation(investigation_id: str, product_id: str | None,
                      trigger: str, order_id: str | None = None) -> None:
    """Runs in a BackgroundTask worker thread. Streams events, stores verdict, executes action."""
    db = SessionLocal()
    try:
        inv = db.get(Investigation, investigation_id)
        inv.status = "running"
        db.commit()
        events.publish(investigation_id, {"type": "status", "status": "running"})

        product = db.get(Product, product_id) if product_id else None
        config = types.GenerateContentConfig(
            system_instruction=AGENT1_SYSTEM_PROMPT,
            tools=[agent1_tools.TOOL],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        contents = [types.Content(
            role="user",
            parts=[types.Part(text=_investigation_request(product, trigger, order_id))],
        )]

        tool_log: list[dict] = []
        for _ in range(MAX_TOOL_STEPS):
            resp = generate_with_retry(model="gemini-3-flash-preview",
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
        _execute_action(db, product, verdict)
        inv.status = "done"
        db.commit()
        events.publish(investigation_id, {"type": "verdict", **verdict.model_dump()})
    except Exception as exc:  # noqa: BLE001 — surface any failure to the trace
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
        model="gemini-3-flash-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Verdict,
            thinking_config=types.ThinkingConfig(thinking_level="high"),
        ),
    )
    return resp.parsed


def _execute_action(db, product: Product | None, verdict: Verdict) -> None:
    """Act on the verdict. Phase 2 executes catalog locks; order effects land in Phase 3."""
    if product is None:
        return
    if verdict.decision == "counterfeit_lock":
        product.status = "locked"
        db.add(CatalogAction(
            id=f"act_{uuid.uuid4().hex[:12]}",
            product_id=product.id,
            action="lock",
            evidence_json={"decision": verdict.decision, "evidence": verdict.evidence},
            created_at=datetime.utcnow(),
        ))

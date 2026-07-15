"""Agent 2 — Listing & Catalog Integrity (Phase 4).

Two LLM touchpoints, both ONE batched structured call (Gemini `response_schema` ->
`response.parsed`, per PLAN §5 / the Phase 1.5 pivot):

  1. `cluster_reviews(product_id)` — groups a product's negative reviews into labelled
     complaint clusters with an AGREEMENT score (share of negative reviews that agree).
     We act on agreement, not raw count (deck promise). Distinct phrasings are sent
     weighted by frequency, so the payload stays tiny and cheap even for 1000 reviews.

  2. `draft_fix(product, cluster)` — for a FIXABLE cluster (fabric/size), drafts a
     corrected size chart / fabric description and writes a `fix_draft` CatalogAction
     (seller_approved=False, before/after stored) for the seller to approve.

The deterministic delisting/tier logic lives in `services/delisting.py` (LLM-free);
this module is the LLM half. Clustering degrades gracefully: on any model error it
returns an empty cluster list so `/audit` still completes deterministically.
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime

from google.genai import types
from pydantic import BaseModel

from ..config import settings
from ..models import CatalogAction, Product
from ..services.rules import (
    CLUSTER_MIN_AGREEMENT,
    FIXABLE_CLUSTERS,
    MAX_CLUSTER_TEXTS,
    NEGATIVE_REVIEW_MAX_RATING,
)
from .gemini_client import generate_with_retry
from .prompts import AGENT2_CLUSTER_INSTRUCTION, AGENT2_FIX_INSTRUCTION

_LABELS = {"fabric_mismatch", "size_issue", "damaged_delivery", "possible_fraud", "other"}


# ---- structured outputs ---------------------------------------------------
class ReviewCluster(BaseModel):
    label: str            # one of _LABELS
    review_ids: list[str]
    agreement: float      # 0-1 share of negative reviews in this cluster
    summary: str


class ClusterResult(BaseModel):
    clusters: list[ReviewCluster]


class SizeRow(BaseModel):
    size: str          # e.g. "M" or "8" or "double"
    measurement: str   # e.g. "38 in" or "UK8 / 26.5 cm"


class FixDraft(BaseModel):
    # NB: no open `dict` field — Gemini's response_schema rejects additionalProperties, so
    # the corrected chart is a LIST of size/measurement rows (normalized to a dict on store).
    field: str            # "size_chart_json" | "fabric_claim"
    corrected_size_chart: list[SizeRow] = []
    corrected_fabric_claim: str = ""
    size_note: str = ""
    rationale: str = ""


def _rows_to_chart(rows: list[SizeRow]) -> dict:
    return {r.size: r.measurement for r in rows}


# a sensible default apparel/footwear chart used by the deterministic fallback draft.
_DEFAULT_SIZE_CHART = {
    "apparel": {"S": "36 in", "M": "38 in", "L": "40 in", "XL": "42 in"},
    "footwear": {"7": "UK7 / 25.5 cm", "8": "UK8 / 26.5 cm", "9": "UK9 / 27.5 cm"},
    "home": {"single": "150x225 cm", "double": "220x240 cm"},
}


def _fallback_draft(product: Product, label: str, drift_note: str) -> FixDraft:
    """Deterministic corrected field when the LLM is unavailable (keeps the seller-approve
    flow demoable offline). Truthful, generic corrections — the seller edits before approving."""
    if label == "size_issue":
        chart = product.size_chart_json or _DEFAULT_SIZE_CHART.get(
            product.category, {"S": "small", "M": "medium", "L": "large"})
        note = "Added a measurement-based size chart." + (f" {drift_note}" if drift_note else "")
        return FixDraft(field="size_chart_json",
                        corrected_size_chart=[SizeRow(size=k, measurement=v) for k, v in chart.items()],
                        size_note=note, rationale="Buyers reported size/fit confusion; added a size chart.")
    # fabric_mismatch
    current = product.fabric_claim or "material"
    corrected = (f"{current} — note: some buyers report a different feel; "
                 "material verified as a blend")
    return FixDraft(field="fabric_claim", corrected_fabric_claim=corrected,
                    rationale="Buyers reported the material differs from the claim; softened to an honest description.")


# ---- clustering -----------------------------------------------------------
def _negative_reviews(product: Product) -> list:
    return [r for r in product.reviews if r.rating <= NEGATIVE_REVIEW_MAX_RATING]


def cluster_reviews(product_id: str, db) -> dict:
    """Cluster a product's negative reviews into labelled complaints with agreement.

    Returns {product_id, negative_count, clusters:[{label, agreement, review_ids,
    summary, actionable}], dominant, actionable}. Distinct complaint phrasings are
    sent to the model weighted by frequency (capped at MAX_CLUSTER_TEXTS); agreement
    is faithful to the full negative set. Empty clusters on no data or model error.
    """
    product = db.get(Product, product_id)
    if product is None:
        return {"error": f"product {product_id} not found", "clusters": []}

    negatives = _negative_reviews(product)
    total = len(negatives)
    if total == 0:
        return {"product_id": product_id, "negative_count": 0, "clusters": [],
                "dominant": None, "actionable": False}

    # group identical phrasings; carry counts + real review ids (cheap, representative payload).
    by_text: dict[str, list[str]] = {}
    for r in negatives:
        by_text.setdefault(r.text.strip(), []).append(r.id)
    ranked = sorted(by_text.items(), key=lambda kv: len(kv[1]), reverse=True)[:MAX_CLUSTER_TEXTS]

    payload_lines = []
    for text, ids in ranked:
        sample_ids = ids[:8]  # a handful of ids per phrasing is enough to anchor the cluster
        payload_lines.append(
            f"- complaint={text!r} count={len(ids)} review_ids={sample_ids}"
        )
    prompt = AGENT2_CLUSTER_INSTRUCTION + "\n\nNegative complaints:\n" + "\n".join(payload_lines)

    try:
        resp = generate_with_retry(
            model=settings.llm_model,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClusterResult,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
        parsed: ClusterResult = resp.parsed
    except Exception as exc:  # noqa: BLE001 — never let clustering break the audit
        print(f"[agent2] cluster_reviews {product_id} failed: {exc}")
        return {"product_id": product_id, "negative_count": total, "clusters": [],
                "dominant": None, "actionable": False, "error": str(exc)}

    # Recompute agreement deterministically from the counts we actually have, so the
    # number is trustworthy regardless of what the model reported. Map each returned
    # review id back to how many buyers shared that phrasing.
    id_weight: dict[str, int] = {}
    for text, ids in by_text.items():
        for i in ids:
            id_weight[i] = len(ids)

    clusters = []
    for c in parsed.clusters:
        label = c.label if c.label in _LABELS else "other"
        # weight the cluster by the buyer-count behind each referenced (sampled) phrasing.
        seen_texts: set[str] = set()
        weight = 0
        for rid in c.review_ids:
            # find the phrasing this id belongs to (ids were sampled, so map via by_text)
            for text, ids in by_text.items():
                if rid in ids and text not in seen_texts:
                    seen_texts.add(text)
                    weight += len(ids)
                    break
        agreement = round(weight / total, 3) if total else 0.0
        clusters.append({
            "label": label,
            "agreement": agreement,
            "review_ids": c.review_ids,
            "summary": c.summary,
            "actionable": agreement >= CLUSTER_MIN_AGREEMENT,
        })

    clusters.sort(key=lambda x: x["agreement"], reverse=True)
    dominant = clusters[0] if clusters else None
    return {
        "product_id": product_id,
        "negative_count": total,
        "clusters": clusters,
        "dominant": dominant,
        "actionable": bool(dominant and dominant["actionable"]),
    }


# ---- fix drafting ---------------------------------------------------------
def draft_fix(product: Product, cluster: dict, db, drift_note: str = "") -> CatalogAction | None:
    """Draft a corrected listing field for a FIXABLE cluster and persist it as a
    `fix_draft` CatalogAction (seller_approved=False) with before/after. Returns the
    action, or None if the cluster is not fixable. One structured LLM call."""
    label = cluster.get("label")
    if label not in FIXABLE_CLUSTERS:
        return None

    before = {
        "size_chart_json": product.size_chart_json,
        "fabric_claim": product.fabric_claim,
    }
    prompt = (
        AGENT2_FIX_INSTRUCTION
        + f"\n\nProduct: {product.title!r} (brand {product.brand}, {product.category})."
        + f"\nCurrent size_chart_json: {product.size_chart_json}."
        + f"\nCurrent fabric_claim: {product.fabric_claim!r}."
        + f"\nDominant complaint: label={label}, summary={cluster.get('summary')!r}, "
        + f"agreement={cluster.get('agreement')}."
        + (f"\nKnown fit drift: {drift_note}" if drift_note else "")
    )
    try:
        resp = generate_with_retry(
            model=settings.llm_model,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FixDraft,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
        draft: FixDraft = resp.parsed
    except Exception as exc:  # noqa: BLE001 — fall back to a deterministic draft, don't drop it
        print(f"[agent2] draft_fix {product.id} LLM failed ({exc}); using deterministic fallback")
        draft = _fallback_draft(product, label, drift_note)

    after = dict(before)
    if label == "size_issue" and draft.corrected_size_chart:
        after["size_chart_json"] = _rows_to_chart(draft.corrected_size_chart)
    if label == "fabric_mismatch" and draft.corrected_fabric_claim:
        after["fabric_claim"] = draft.corrected_fabric_claim

    action = CatalogAction(
        id=f"act_{uuid.uuid4().hex[:12]}",
        product_id=product.id,
        action="fix_draft",
        evidence_json={
            "cluster": label,
            "summary": cluster.get("summary"),
            "agreement": cluster.get("agreement"),
            "field": draft.field,
            "before": before,
            "after": after,
            "size_note": draft.size_note,
            "rationale": draft.rationale,
        },
        seller_approved=False,
        created_at=datetime.utcnow(),
    )
    db.add(action)
    return action

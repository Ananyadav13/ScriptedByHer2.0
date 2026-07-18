"""Agent 1 tool layer: Gemini FunctionDeclarations + a dispatch table.

The declarations are schema-only (what the model sees). Actual execution happens
in `dispatch`, which loads ORM objects and calls the deterministic services in
`app.services.risk_checks`. Kept separate so the orchestrator can log/stream each
call. The three risk tools touch NO LLM; the 4th (`check_video_reviews`) is a
multimodal sub-call and is imported lazily inside `dispatch` so this module's
deterministic tools stay LLM-free at import time.
"""
from __future__ import annotations

from google.genai import types

from ..models import Buyer, Hub, Order, Product
from ..services import risk_checks


def _str_param(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


CHECK_CATALOG_RISK = types.FunctionDeclaration(
    name="check_catalog_risk",
    description=(
        "Price-vs-MRP ratio, review-burst statistics, the trustworthy (new-account-discounted) "
        "rating, order volume and quality-check-video SLA status for a product."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"product_id": _str_param("The product to analyze.")},
        required=["product_id"],
    ),
)

CHECK_SELLER_PROFILE = types.FunctionDeclaration(
    name="check_seller_profile",
    description="Seller account age, rating, and trust flags for the product's seller.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"product_id": _str_param("The product whose seller to profile.")},
        required=["product_id"],
    ),
)

CHECK_DELIVERY_SIGNALS = types.FunctionDeclaration(
    name="check_delivery_signals",
    description="OTP-vs-items, hub anomaly, and buyer claim-history signals for a delivery dispute.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={"order_id": _str_param("The order under dispute.")},
        required=["order_id"],
    ),
)

CHECK_MEDIA_EVIDENCE = types.FunctionDeclaration(
    name="check_media_evidence",
    description=(
        "ADVISORY vision scan, VARIANT-AWARE. The seller's ONE listing video is distilled into "
        "variant-invariant QUALITY attributes (weave, sheen, texture, opacity, stitch, drape); "
        "the buyer's complaint media is read into the same attributes and a deterministic engine "
        "diffs ONLY those. A dispute on a different COLOURWAY is therefore never a mismatch on "
        "colour alone — colour/shade are excluded by construction. Returns which attributes were "
        "compared vs ignored, whether they materially diverge, a CONFIDENCE, variant context, and "
        "a separate colour_note for a genuine wrong-colour claim. Call ONLY when a material/quality "
        "claim is in doubt (a material dispute with buyer media, or a low trustworthy rating on a "
        "product making a material claim). This tool NEVER decides a punishment — it recommends."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "product_id": _str_param("The product to inspect."),
            "order_id": _str_param("Optional: the disputed order whose buyer evidence to use."),
        },
        required=["product_id"],
    ),
)

DECLARATIONS = [CHECK_CATALOG_RISK, CHECK_SELLER_PROFILE, CHECK_DELIVERY_SIGNALS, CHECK_MEDIA_EVIDENCE]
TOOL = types.Tool(function_declarations=DECLARATIONS)


def dispatch(name: str, args: dict, db) -> dict:
    """Execute a tool call against the DB. Returns a JSON-serializable dict."""
    if name == "check_catalog_risk":
        product = db.get(Product, args["product_id"])
        if not product:
            return {"error": f"product {args.get('product_id')} not found"}
        order_count = db.query(Order).filter(Order.product_id == product.id).count()
        return {
            "price_mrp": risk_checks.price_mrp_risk(product),
            "review_burst": risk_checks.review_burst_risk(product),
            "trustworthy_rating": risk_checks.trustworthy_rating(product),
            # context for the video-scan gate + the hard-lock confidence floor
            "fabric_claim": product.fabric_claim,
            "video_review_count": sum(1 for r in product.reviews if r.has_video and r.video_path),
            "order_volume": risk_checks.order_volume(order_count),
            "qc_sla": risk_checks.qc_sla_status(product),
        }
    if name == "check_seller_profile":
        product = db.get(Product, args["product_id"])
        if not product or not product.seller:
            return {"error": f"seller for product {args.get('product_id')} not found"}
        return risk_checks.seller_profile(product.seller)
    if name == "check_delivery_signals":
        order = db.get(Order, args["order_id"])
        if not order:
            return {"error": f"order {args.get('order_id')} not found"}
        buyer = db.get(Buyer, order.buyer_id)
        hub = db.get(Hub, order.hub_id) if order.hub_id else None
        return risk_checks.delivery_signals(order, buyer, hub)
    if name == "check_media_evidence":
        from . import vision  # lazy: keeps the deterministic tools LLM-free at import
        return vision.check_media_evidence(args["product_id"], db, args.get("order_id"))
    return {"error": f"unknown tool {name}"}

"""Agent 1 tool layer: Gemini FunctionDeclarations + a dispatch table.

The declarations are schema-only (what the model sees). Actual execution happens
in `dispatch`, which loads ORM objects and calls the deterministic services in
`app.services.risk_checks`. Kept separate so the orchestrator can log/stream each
call and so nothing here imports the LLM client.
"""
from __future__ import annotations

from google.genai import types

from ..models import Order, Product, Buyer
from ..services import risk_checks


def _str_param(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


CHECK_CATALOG_RISK = types.FunctionDeclaration(
    name="check_catalog_risk",
    description="Price-vs-MRP ratio, image-authenticity match, and review-burst statistics for a product.",
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

DECLARATIONS = [CHECK_CATALOG_RISK, CHECK_SELLER_PROFILE, CHECK_DELIVERY_SIGNALS]
TOOL = types.Tool(function_declarations=DECLARATIONS)


def dispatch(name: str, args: dict, db) -> dict:
    """Execute a tool call against the DB. Returns a JSON-serializable dict."""
    if name == "check_catalog_risk":
        product = db.get(Product, args["product_id"])
        if not product:
            return {"error": f"product {args.get('product_id')} not found"}
        return {
            "price_mrp": risk_checks.price_mrp_risk(product),
            "image_match": risk_checks.image_match_risk(product),
            "review_burst": risk_checks.review_burst_risk(product),
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
        return risk_checks.delivery_signals(order, buyer)
    return {"error": f"unknown tool {name}"}

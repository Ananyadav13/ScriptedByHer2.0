"""Pydantic DTOs + agent structured outputs."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---- Agent 1 verdict (via Gemini response_schema -> response.parsed) ----
class Verdict(BaseModel):
    # decision: counterfeit_lock | request_qc_video | relabel_required | notify_only |
    #           hold_pending_fix | ban | refund_fast_track | standard_process |
    #           manual_review | recommend_review | cleared | authentic
    decision: str
    confidence: float
    evidence: list[str]
    action: str
    buyer_explanation: str
    # Advisory fields — populated when the agent RECOMMENDS to the manager rather than
    # acting (esp. uncertain media comparisons). Empty for autonomous outcomes.
    recommended_action: str = ""
    suggested_remedy: str = ""


# ---- API response DTOs ----
class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rating: int
    text: str
    reviewer_account_age_days: int
    has_video: bool
    created_at: datetime | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    seller_id: str
    title: str
    brand: str
    category: str
    price: float
    mrp: float
    images: list
    fabric_claim: str | None
    # the seller's real size/measurement spec — the product page renders THIS rather than
    # guessing from category, so a missing/placeholder chart is visible to the buyer.
    size_chart_json: dict | None = None
    status: str
    knockoff_flag: bool = False
    buyer_tip: str | None = None
    rating: float = 0.0          # avg star rating (computed from reviews)
    rating_count: int = 0        # total star ratings (incl. rating-only, no text)
    review_count: int = 0        # written reviews only — the subset with text


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    colour: str | None = None
    is_listing_reference: bool = False   # the one colourway the listing video actually shows


class ProductDetail(ProductOut):
    reviews: list[ReviewOut] = []
    variants: list[VariantOut] = []
    # locked/on_hold/needs_info listings expose WHY + the latest agent action
    lock_reason: str | None = None
    latest_action: str | None = None
    qc_requested: bool = False

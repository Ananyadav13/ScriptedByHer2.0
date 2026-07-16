"""Pydantic DTOs + agent structured outputs."""
from datetime import datetime

from pydantic import BaseModel


# ---- Agent 1 verdict (Phase 2 uses via Gemini response_schema -> response.parsed) ----
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
    id: str
    rating: int
    text: str
    reviewer_account_age_days: int
    has_video: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: str
    seller_id: str
    title: str
    brand: str
    category: str
    price: float
    mrp: float
    images: list
    fabric_claim: str | None
    status: str
    knockoff_flag: bool = False
    buyer_tip: str | None = None
    rating: float = 0.0          # avg star rating (computed from reviews)
    rating_count: int = 0        # number of ratings/reviews

    class Config:
        from_attributes = True


class ProductDetail(ProductOut):
    reviews: list[ReviewOut] = []
    # locked/on_hold/needs_info listings expose WHY + the latest agent action
    lock_reason: str | None = None
    latest_action: str | None = None
    qc_requested: bool = False

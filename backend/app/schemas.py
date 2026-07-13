"""Pydantic DTOs + agent structured outputs."""
from pydantic import BaseModel


# ---- Agent 1 verdict (Phase 2 uses via Gemini response_schema -> response.parsed) ----
class Verdict(BaseModel):
    decision: str          # authentic | counterfeit_lock | refund_fast_track | manual_review | standard_process | cleared
    confidence: float
    evidence: list[str]
    action: str
    buyer_explanation: str


# ---- API response DTOs ----
class ReviewOut(BaseModel):
    id: str
    rating: int
    text: str
    reviewer_account_age_days: int
    has_video: bool

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

    class Config:
        from_attributes = True


class ProductDetail(ProductOut):
    reviews: list[ReviewOut] = []

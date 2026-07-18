"""ORM models. JSON-ish fields stored as SQLAlchemy JSON."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .time_utils import utcnow


class Manager(Base):
    """Meesho business manager — owns a book of sellers (~100:1). Every agent lock
    lands in this manager's review queue; the ABSOLUTE unlock/delete decision is theirs."""
    __tablename__ = "managers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    sellers: Mapped[list["Seller"]] = relationship(back_populates="manager")


class Seller(Base):
    __tablename__ = "sellers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    account_created_at: Mapped[datetime] = mapped_column(DateTime)
    trust_flags: Mapped[list] = mapped_column(JSON, default=list)
    case_count: Mapped[int] = mapped_column(Integer, default=0)   # substantiated cases in window
    banned: Mapped[bool] = mapped_column(default=False)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("managers.id"), nullable=True)

    manager: Mapped["Manager"] = relationship(back_populates="sellers")
    products: Mapped[list["Product"]] = relationship(back_populates="seller")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    seller_id: Mapped[str] = mapped_column(ForeignKey("sellers.id"))
    title: Mapped[str] = mapped_column(String)
    brand: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    mrp: Mapped[float] = mapped_column(Float)
    images: Mapped[list] = mapped_column(JSON, default=list)
    size_chart_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fabric_claim: Mapped[str | None] = mapped_column(String, nullable=True)
    # Star ratings INCLUDING rating-only (no text) submissions. Real listings carry far
    # more ratings than written reviews (e.g. 7470 ratings / 2425 reviews), so this is
    # stored rather than derived. 0 => fall back to the text-review count.
    # Display only: every DECISION still runs on the genuine `reviews` rows, never on this.
    ratings_total: Mapped[int] = mapped_column(Integer, default=0)
    # seller's authentic listing-time video (the canonical reference for media compare).
    # A seller films this ONCE, for ONE variant — see `quality_fingerprint_json`.
    listing_video_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # The "golden fields": variant-invariant quality attributes distilled from the listing
    # video (weave/sheen/texture/opacity/stitch/drape). Extracted once and reused for EVERY
    # variant, because a seller cannot film a video per colourway. Disputes are judged
    # against this, never against raw listing frames — comparing a blue kurti to a black
    # listing video would make colour the loudest "discrepancy" and false-flag the seller.
    quality_fingerprint_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # image URLs of the sampled listing-video keyframes, shown side-by-side against the
    # buyer's photos in a dispute so a human can SEE what the fingerprint compared.
    listing_frame_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # active/locked/delisted/correction_window/suspended/on_hold/needs_info/flagged
    # `flagged` = agent RECOMMENDS manager review (advisory) — sale continues, no buyer impact
    status: Mapped[str] = mapped_column(String, default="active")
    knockoff_flag: Mapped[bool] = mapped_column(default=False)  # relabeled as honest knockoff
    buyer_tip: Mapped[str | None] = mapped_column(Text, nullable=True)  # gentle at-purchase note
    # Counterfeit flow steps 3-4: seller quality-check video request + latency SLA.
    qc_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    qc_responded: Mapped[bool] = mapped_column(default=False)

    seller: Mapped["Seller"] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(back_populates="product")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")


class ProductVariant(Base):
    """One purchasable colourway/option of a product (Meesho sells "the same kurti" in
    black/blue/red). The seller's listing video depicts exactly ONE of these — the one
    flagged `is_listing_reference` — which is why a dispute on any OTHER variant must be
    judged on the product's variant-invariant quality fingerprint, not on the video."""
    __tablename__ = "product_variants"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    name: Mapped[str] = mapped_column(String)              # display label, e.g. "Blue"
    colour: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)   # None => product price
    images: Mapped[list] = mapped_column(JSON, default=list)
    in_stock: Mapped[bool] = mapped_column(default=True)
    # True for the single variant the seller actually filmed for the listing video.
    is_listing_reference: Mapped[bool] = mapped_column(default=False)

    product: Mapped["Product"] = relationship(back_populates="variants")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    reviewer_account_age_days: Mapped[int] = mapped_column(Integer)
    has_video: Mapped[bool] = mapped_column(default=False)
    video_path: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="manual")  # manual | image | video

    product: Mapped["Product"] = relationship(back_populates="reviews")


class Buyer(Base):
    __tablename__ = "buyers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kept_size_history_json: Mapped[dict] = mapped_column(JSON, default=dict)
    claim_history: Mapped[dict] = mapped_column(JSON, default=dict)  # {count, outcomes: []}
    case_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[bool] = mapped_column(default=False)


class Hub(Base):
    """Delivery partner / logistics hub — the third fraud actor.

    Hubs are never auto-banned (infrastructure); a fraudulent hub triggers an
    IMMEDIATE notification to the support/ops team (see orchestrator).
    """
    __tablename__ = "hubs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    region: Mapped[str] = mapped_column(String, default="")
    score: Mapped[float] = mapped_column(Float, default=5.0)   # 0-5 reliability score
    case_count: Mapped[int] = mapped_column(Integer, default=0)  # disputes traced to this hub (window)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    # which colourway actually shipped — decides whether a media dispute is a CROSS-VARIANT
    # comparison (buyer's blue vs a black listing video) and must ignore colour.
    variant_id: Mapped[str | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    hub_id: Mapped[str | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    otp_scan_count: Mapped[int] = mapped_column(Integer, default=0)
    items_count: Mapped[int] = mapped_column(Integer, default=1)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hub_anomaly_flag: Mapped[bool] = mapped_column(default=False)
    geo_photo_verified: Mapped[bool] = mapped_column(default=False)  # geo-tagged proof-of-delivery
    # buyer-supplied dispute evidence: list of media paths (photos OR videos)
    buyer_evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    # pre-read quality attributes of the buyer's evidence (the "golden fields" as seen in the
    # buyer's photos). Seeded for the demo so the fingerprint comparison is deterministic and
    # runs with zero LLM quota; when absent, vision reads the frames live instead.
    buyer_evidence_fingerprint_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # what the buyer actually claimed. Decides whether COLOUR may be compared at all:
    # a "wrong colour sent" complaint must be heard, a fabric complaint must not be
    # derailed by the colourway (see services/quality_fingerprint).
    claim_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="delivered")  # delivered/refunded/manual_review


class SizeDrift(Base):
    __tablename__ = "size_drift"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    label_size: Mapped[str] = mapped_column(String)
    true_measurement_delta: Mapped[float] = mapped_column(Float)  # +/- sizes; e.g. -1 = runs 1 size small
    sample_size: Mapped[int] = mapped_column(Integer, default=0)


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    trigger: Mapped[str] = mapped_column(String)  # pre_purchase/catalog_gate/post_delivery
    status: Mapped[str] = mapped_column(String, default="queued")  # queued/running/done/error
    tool_calls_log_json: Mapped[list] = mapped_column(JSON, default=list)
    verdict_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CatalogAction(Base):
    __tablename__ = "catalog_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    action: Mapped[str] = mapped_column(String)  # lock/delist/suspend/correction/fix_draft/logistics/reverify
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    seller_approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    """Outbound message to a seller / support / ops team — how the graduated
    ladder's 'notify' and 'immediate hub escalation' actions become real."""
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    audience: Mapped[str] = mapped_column(String)   # seller | manager | ops | buyer
    recipient_id: Mapped[str | None] = mapped_column(String, nullable=True)  # seller/manager/buyer id
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String, default="normal")  # normal | high | immediate
    related_id: Mapped[str | None] = mapped_column(String, nullable=True)  # product/order/hub id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

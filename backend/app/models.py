"""ORM models — PLAN.md §3. JSON-ish fields stored as SQLAlchemy JSON."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


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
    # active/locked/delisted/correction_window/suspended/on_hold/needs_info
    status: Mapped[str] = mapped_column(String, default="active")
    knockoff_flag: Mapped[bool] = mapped_column(default=False)  # relabeled as honest knockoff
    buyer_tip: Mapped[str | None] = mapped_column(Text, nullable=True)  # gentle at-purchase note

    seller: Mapped["Seller"] = relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(back_populates="product")


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
    hub_id: Mapped[str | None] = mapped_column(ForeignKey("hubs.id"), nullable=True)
    otp_scan_count: Mapped[int] = mapped_column(Integer, default=0)
    items_count: Mapped[int] = mapped_column(Integer, default=1)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hub_anomaly_flag: Mapped[bool] = mapped_column(default=False)
    geo_photo_verified: Mapped[bool] = mapped_column(default=False)  # geo-tagged proof-of-delivery
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CatalogAction(Base):
    __tablename__ = "catalog_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    action: Mapped[str] = mapped_column(String)  # lock/delist/suspend/correction/fix_draft/logistics/reverify
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    seller_approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """Outbound message to a seller / support / ops team — how the graduated
    ladder's 'notify' and 'immediate hub escalation' actions become real."""
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    audience: Mapped[str] = mapped_column(String)   # seller | support | ops
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String, default="normal")  # normal | high | immediate
    related_id: Mapped[str | None] = mapped_column(String, nullable=True)  # product/order/hub id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

"""Seed the 6 golden-path scenarios (PLAN.md §3). Idempotent: drops + recreates in dev.

Stable IDs are load-bearing — frontend scenario buttons and later phases reference them.
"""
from datetime import datetime, timedelta

from .db import Base, SessionLocal, engine
from .models import (
    Buyer,
    CatalogAction,
    Hub,
    Investigation,
    Order,
    Product,
    Review,
    Seller,
    SizeDrift,
)

NOW = datetime.utcnow()


def _dt(days_ago: float) -> datetime:
    return NOW - timedelta(days=days_ago)


def reset_and_seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
        db.commit()
    finally:
        db.close()


def _seed(db):
    # ---------- SELLERS ----------
    sellers = [
        Seller(id="seller_counterfeit", name="LuxDeals Store", rating=3.1,
               account_created_at=_dt(20), trust_flags=["new_account_cluster"]),
        Seller(id="seller_viral", name="TrendyThreads", rating=4.4,
               account_created_at=_dt(900), trust_flags=[]),
        Seller(id="seller_kurti", name="EthnicWeave", rating=3.9,
               account_created_at=_dt(500), trust_flags=[]),
        Seller(id="seller_shoes", name="StepUp Footwear", rating=4.1,
               account_created_at=_dt(600), trust_flags=[]),
        Seller(id="seller_lowrated", name="BargainBin", rating=1.8,
               account_created_at=_dt(300), trust_flags=["quality_complaints"],
               case_count=5),  # repeat offender -> ban path
        Seller(id="seller_fixable", name="HomeComfort", rating=2.4,
               account_created_at=_dt(400), trust_flags=[]),
        # honest seller of a well-loved cheap knockoff -> relabel path (not ban)
        Seller(id="seller_knockoff", name="StreetStyle Optics", rating=4.2,
               account_created_at=_dt(450), trust_flags=[]),
    ]
    db.add_all(sellers)

    # ---------- PRODUCTS ----------
    products = [
        # 1. Counterfeit: brand far below MRP
        Product(id="prod_counterfeit_rolex", seller_id="seller_counterfeit",
                title="Rolex Submariner Watch - Premium", brand="Rolex", category="watches",
                price=599, mrp=850000, images=["rolex_stock.jpg"],
                fabric_claim=None, status="active"),
        # 2. Honest viral seller: legit product, sudden volume, but old real accounts
        Product(id="prod_viral_honest", seller_id="seller_viral",
                title="Oversized Cotton T-Shirt (Viral)", brand="TrendyThreads", category="apparel",
                price=499, mrp=999, images=["tshirt_real.jpg"],
                fabric_claim="100% cotton", status="active"),
        # 3. Fabric mismatch: claims cotton, reviews say synthetic (video in Phase 3)
        Product(id="prod_fabric_kurti", seller_id="seller_kurti",
                title="Pure Cotton Anarkali Kurti", brand="EthnicWeave", category="apparel",
                price=799, mrp=1599, images=["kurti.jpg"],
                fabric_claim="pure cotton", status="active",
                size_chart_json={"S": "36", "M": "38", "L": "40"}),
        # 4. Size drift: brand runs small (see SizeDrift + buyer history)
        Product(id="prod_size_shoes", seller_id="seller_shoes",
                title="Running Shoes - Lightweight", brand="StepUp", category="footwear",
                price=1299, mrp=2499, images=["shoes.jpg"],
                fabric_claim=None, status="active",
                size_chart_json={"7": "UK7", "8": "UK8", "9": "UK9"}),
        # 5. Low-rated fraud cluster -> suspend (Phase 4 audit)
        Product(id="prod_lowrated_fraud", seller_id="seller_lowrated",
                title="Wireless Earbuds Pro Max", brand="BargainBin", category="electronics",
                price=699, mrp=2999, images=["earbuds.jpg"],
                fabric_claim=None, status="active"),
        # 6. Fixable gaps -> correction window (Phase 4 audit)
        Product(id="prod_fixable_bedsheet", seller_id="seller_fixable",
                title="Cotton Bedsheet Double", brand="HomeComfort", category="home",
                price=549, mrp=1299, images=["bedsheet.jpg"],
                fabric_claim="cotton", status="active",
                size_chart_json=None),
        # 7. Loved knockoff: branded-style, far below MRP (counterfeit signal) BUT
        #    genuinely high trustworthy rating -> relabel_required, NOT a ban.
        Product(id="prod_knockoff_loved", seller_id="seller_knockoff",
                title="Aviator Sunglasses (Rayban-inspired)", brand="Rayban", category="accessories",
                price=499, mrp=7999, images=["aviator.jpg"],
                fabric_claim=None, status="active"),
        # benign filler (realistic catalog, no flags)
        Product(id="prod_normal_mug", seller_id="seller_viral",
                title="Ceramic Coffee Mug 350ml", brand="TrendyThreads", category="home",
                price=249, mrp=399, images=["mug.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_normal_notebook", seller_id="seller_shoes",
                title="A5 Ruled Notebook 200 pages", brand="StepUp", category="stationery",
                price=99, mrp=199, images=["notebook.jpg"], fabric_claim=None, status="active"),
    ]
    db.add_all(products)

    # ---------- REVIEWS ----------
    reviews = []
    # counterfeit: burst of 5-star from very new accounts
    for i in range(12):
        reviews.append(Review(id=f"rev_cf_{i}", product_id="prod_counterfeit_rolex",
                              rating=5, text="Amazing genuine watch!!", created_at=_dt(2),
                              reviewer_account_age_days=2))
    # viral honest: burst of reviews but from OLD accounts (not flagged)
    for i in range(15):
        reviews.append(Review(id=f"rev_vi_{i}", product_id="prod_viral_honest",
                              rating=5, text="Great fit, soft cotton, went viral on reels",
                              created_at=_dt(3), reviewer_account_age_days=400 + i * 20))
    # fabric kurti: negative cluster, one flagged for video (Phase 3 attaches video)
    kurti_neg = [
        ("Fabric feels synthetic, not cotton at all", 2, True),
        ("Shrank after first wash", 2, False),
        ("Shiny polyester look, misleading listing", 1, False),
        ("Not breathable, definitely not pure cotton", 2, True),
        ("Color faded, cheap material", 2, False),
    ]
    for i, (t, r, vid) in enumerate(kurti_neg):
        reviews.append(Review(id=f"rev_ku_{i}", product_id="prod_fabric_kurti",
                              rating=r, text=t, created_at=_dt(10 + i),
                              reviewer_account_age_days=300, has_video=vid))
    # low-rated fraud: many low reviews with fraud-y language
    fraud_txt = ["Fake product, not as described", "Scam, stopped working in a day",
                 "Counterfeit, avoid this seller", "Never delivered what was shown"]
    for i in range(1000):  # count matters for delisting tier
        reviews.append(Review(id=f"rev_lr_{i}", product_id="prod_lowrated_fraud",
                              rating=1, text=fraud_txt[i % 4], created_at=_dt(30 + i % 60),
                              reviewer_account_age_days=200))
    # loved knockoff: genuine, mostly-happy reviews from ESTABLISHED accounts,
    # spread over recent weeks -> high trustworthy rating despite the low price.
    knock_txt = ["Looks exactly like the real ones, great value", "Solid build for the price",
                 "Everyone thinks they're original", "Good UV protection, happy with it",
                 "Not the real brand but excellent quality"]
    for i in range(20):
        reviews.append(Review(id=f"rev_kn_{i}", product_id="prod_knockoff_loved",
                              rating=5 if i % 5 else 4, text=knock_txt[i % 5],
                              created_at=_dt(i * 3), reviewer_account_age_days=200 + i * 15))
    # fixable: many mid reviews about fixable gaps (missing size info / thin)
    fix_txt = ["Thinner than expected", "No size chart, guessed wrong",
               "Decent but description lacks detail", "Okay quality, poor listing info"]
    for i in range(800):
        reviews.append(Review(id=f"rev_fx_{i}", product_id="prod_fixable_bedsheet",
                              rating=2, text=fix_txt[i % 4], created_at=_dt(30 + i % 60),
                              reviewer_account_age_days=350))
    db.add_all(reviews)

    # ---------- BUYERS ----------
    db.add_all([
        Buyer(id="buyer_normal", kept_size_history_json={"StepUp:footwear": "8", "generic:apparel": "M"},
              claim_history={"count": 0, "outcomes": []}),
        Buyer(id="buyer_serial_claimer",
              kept_size_history_json={},
              claim_history={"count": 7, "outcomes": ["refunded", "refunded", "denied",
                                                       "refunded", "denied", "refunded", "refunded"]}),
    ])

    # ---------- HUBS (delivery partners) ----------
    db.add_all([
        # fraudulent hub: many disputes traced here -> immediate ops escalation
        Hub(id="hub_faulty", name="Sector-9 Logistics Hub", region="North",
            score=1.9, case_count=6),
        Hub(id="hub_normal", name="Central Fulfilment Hub", region="Central",
            score=4.6, case_count=0),
    ])

    # ---------- ORDERS ----------
    db.add_all([
        # multi-item, single OTP scan, hub anomaly, no geo-photo, routed via the faulty
        # hub -> refund fast-track (two independent signals) + hub escalation.
        Order(id="order_otp_dispute", buyer_id="buyer_normal", product_id="prod_size_shoes",
              hub_id="hub_faulty", otp_scan_count=1, items_count=3, delivered_at=_dt(1),
              hub_anomaly_flag=True, geo_photo_verified=False, status="delivered"),
        # serial claimer order -> manual review (routed via a clean hub)
        Order(id="order_serial", buyer_id="buyer_serial_claimer", product_id="prod_fabric_kurti",
              hub_id="hub_normal", otp_scan_count=1, items_count=1, delivered_at=_dt(1),
              hub_anomaly_flag=False, geo_photo_verified=True, status="delivered"),
    ])

    # ---------- SIZE DRIFT ----------
    db.add_all([
        SizeDrift(brand="StepUp", category="footwear", label_size="8",
                  true_measurement_delta=-1.0, sample_size=214),  # runs 1 size small
    ])

    db.add_all([])  # investigations / catalog_actions start empty

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
    Manager,
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
    """Dev: drop + recreate + seed. Destroys existing data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
        db.commit()
    finally:
        db.close()


def create_and_seed_if_empty():
    """Persistent deployments: create tables if missing, seed only when empty.
    Never drops — data, logs and history survive restarts (no data loss)."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).first() is None:
            _seed(db)
            db.commit()
    finally:
        db.close()


def _seed(db):
    # ---------- MANAGERS (business managers own a book of sellers) ----------
    db.add_all([
        Manager(id="mgr_north", name="Priya (North zone)"),
        Manager(id="mgr_south", name="Arjun (South zone)"),
    ])

    # ---------- SELLERS (manager_id links each to a business manager) ----------
    sellers = [
        Seller(id="seller_counterfeit", name="LuxDeals Store", rating=3.1,
               account_created_at=_dt(20), trust_flags=["new_account_cluster"],
               manager_id="mgr_north"),
        Seller(id="seller_viral", name="TrendyThreads", rating=4.4,
               account_created_at=_dt(900), trust_flags=[], manager_id="mgr_south"),
        Seller(id="seller_kurti", name="EthnicWeave", rating=3.9,
               account_created_at=_dt(500), trust_flags=[], manager_id="mgr_north"),
        Seller(id="seller_shoes", name="StepUp Footwear", rating=4.1,
               account_created_at=_dt(600), trust_flags=[], manager_id="mgr_south"),
        Seller(id="seller_lowrated", name="BargainBin", rating=1.8,
               account_created_at=_dt(300), trust_flags=["quality_complaints"],
               case_count=5, manager_id="mgr_north"),  # repeat offender -> ban path
        Seller(id="seller_fixable", name="HomeComfort", rating=2.4,
               account_created_at=_dt(400), trust_flags=[], manager_id="mgr_south"),
        # honest seller of a well-loved cheap knockoff -> relabel path (not ban)
        Seller(id="seller_knockoff", name="StreetStyle Optics", rating=4.2,
               account_created_at=_dt(450), trust_flags=[], manager_id="mgr_north"),
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
        # 3. Fabric mismatch: claims cotton, reviews say synthetic (hybrid media, Phase 3).
        #    listing_video_path = the seller's authentic listing video (reference); left
        #    None until a real recording is dropped into media/videos/ (e.g. "kurti_listing.mp4").
        Product(id="prod_fabric_kurti", seller_id="seller_kurti",
                title="Pure Cotton Anarkali Kurti", brand="EthnicWeave", category="apparel",
                price=799, mrp=1599, images=["kurti.jpg"],
                fabric_claim="pure cotton", status="active", listing_video_path=None,
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
        # 6b. Delivery-fault: a GOOD seller's product ruined by a bad courier -> Agent-2
        #     audit routes to logistics referral, NO seller-rating penalty (fairness rule).
        Product(id="prod_damaged_courier", seller_id="seller_shoes",
                title="Glass Water Bottle 1L", brand="StepUp", category="home",
                price=299, mrp=699, images=["bottle.jpg"], fabric_claim=None, status="active"),
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
    # counterfeit: burst of 5-star from very new accounts (varied generic praise —
    # the giveaway is that EVERY reviewer is a 2-day-old account, not the wording).
    cf_txt = [
        "Amazing genuine watch, looks so premium!",
        "Original piece, worth every rupee 😍",
        "100% authentic, exactly like the showroom",
        "Best watch I've bought online, superb quality",
        "Loved it, feels so premium and real",
        "Genuine product and super fast delivery",
    ]
    for i in range(12):
        reviews.append(Review(id=f"rev_cf_{i}", product_id="prod_counterfeit_rolex",
                              rating=5, text=cf_txt[i % len(cf_txt)], created_at=_dt(2),
                              reviewer_account_age_days=2))
    # viral honest: burst of reviews but from OLD accounts (not flagged)
    vi_txt = [
        "Great fit, soft cotton, went viral on reels!",
        "So comfy, perfect for summer 👌",
        "Love the oversized fit, true to size",
        "Fabric is really soft, totally worth it",
        "Trendy and comfortable, highly recommend",
    ]
    for i in range(15):
        reviews.append(Review(id=f"rev_vi_{i}", product_id="prod_viral_honest",
                              rating=5, text=vi_txt[i % len(vi_txt)],
                              created_at=_dt(3), reviewer_account_age_days=400 + i * 20))
    # fabric kurti: negative cluster; two reviews carry videos (Phase 3 vision).
    # video_path points at a REAL review-video asset dropped into media/videos/
    # (or a frames/<dir> of stills). Left None until the physical recordings are
    # supplied; the vision tool then reports available=False and the agent decides
    # on the text signals alone — no fabricated evidence. Wire the filenames here.
    KURTI_VIDEO = {0: None, 3: None}  # e.g. {0: "kurti_review_synthetic_1.mp4", 3: "kurti_review_2.mp4"}
    kurti_neg = [
        ("Fabric feels synthetic, not cotton at all", 2),
        ("Shrank after first wash", 2),
        ("Shiny polyester look, misleading listing", 1),
        ("Not breathable, definitely not pure cotton", 2),
        ("Color faded, cheap material", 2),
    ]
    for i, (t, r) in enumerate(kurti_neg):
        vpath = KURTI_VIDEO.get(i)
        reviews.append(Review(id=f"rev_ku_{i}", product_id="prod_fabric_kurti",
                              rating=r, text=t, created_at=_dt(10 + i),
                              reviewer_account_age_days=300,
                              has_video=(i in KURTI_VIDEO), video_path=vpath))
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
    # fixable: many mid reviews dominated by a SIZE complaint (missing size chart) ->
    # Agent-2 audit trips a delist tier and routes to correction_window + a fix draft.
    # 1000 recent established-account reviews at 2★ -> trustworthy ~2.0, trips <3.0/1000+.
    fix_txt = ["No size chart, ordered the wrong size", "Size unclear, too small for my bed",
               "Size chart missing, had to guess the measurement", "Runs small, size details lacking"]
    for i in range(1000):
        reviews.append(Review(id=f"rev_fx_{i}", product_id="prod_fixable_bedsheet",
                              rating=2, text=fix_txt[i % 4], created_at=_dt(20 + i % 60),
                              reviewer_account_age_days=350))
    # delivery-fault: a well-rated SELLER's product wrecked by a bad courier -> the audit
    # trips a tier but the dominant complaint is damaged_delivery -> logistics referral,
    # NO seller-rating penalty (the fairness rule: faults are the hub's, not the seller's).
    dmg_txt = ["Arrived broken, packaging crushed", "Damaged in transit, box destroyed",
               "Item shattered on delivery", "Received cracked, courier mishandled it"]
    for i in range(800):
        reviews.append(Review(id=f"rev_dmg_{i}", product_id="prod_damaged_courier",
                              rating=1, text=dmg_txt[i % 4], created_at=_dt(20 + i % 60),
                              reviewer_account_age_days=300))
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
    orders = [
        # multi-item, single OTP scan, hub anomaly, no geo-photo, routed via the faulty
        # hub -> refund fast-track (two independent signals) + hub escalation.
        Order(id="order_otp_dispute", buyer_id="buyer_normal", product_id="prod_size_shoes",
              hub_id="hub_faulty", otp_scan_count=1, items_count=3, delivered_at=_dt(1),
              hub_anomaly_flag=True, geo_photo_verified=False, status="delivered"),
        # serial claimer order -> manual review (routed via a clean hub)
        Order(id="order_serial", buyer_id="buyer_serial_claimer", product_id="prod_fabric_kurti",
              hub_id="hub_normal", otp_scan_count=1, items_count=1, delivered_at=_dt(1),
              hub_anomaly_flag=False, geo_photo_verified=True, status="delivered"),
        # clean buyer, material dispute ("received synthetic, not cotton") WITH photo/video
        # evidence -> hybrid check_media_evidence -> ADVISORY recommend_review to the manager.
        # buyer_evidence_json holds media paths; left empty until real buyer media is supplied.
        Order(id="order_fabric_dispute", buyer_id="buyer_normal", product_id="prod_fabric_kurti",
              hub_id="hub_normal", otp_scan_count=1, items_count=1, delivered_at=_dt(2),
              hub_anomaly_flag=False, geo_photo_verified=True, buyer_evidence_json=[],
              status="delivered"),
    ]
    # Order volume for the counterfeit so it clears the confidence floor
    # (>= MIN_ORDERS_FOR_ACTION) and still HARD-locks — a fake watch 24 people
    # actually bought is exactly why we lock. Fewer orders -> request_qc_video.
    for i in range(24):
        orders.append(Order(id=f"order_cf_{i}", buyer_id="buyer_normal",
                            product_id="prod_counterfeit_rolex", hub_id="hub_normal",
                            otp_scan_count=1, items_count=1, delivered_at=_dt(5 + i % 20),
                            hub_anomaly_flag=False, geo_photo_verified=True, status="delivered"))
    db.add_all(orders)

    # ---------- SIZE DRIFT ----------
    db.add_all([
        SizeDrift(brand="StepUp", category="footwear", label_size="8",
                  true_measurement_delta=-1.0, sample_size=214),  # runs 1 size small
    ])

    db.add_all([])  # investigations / catalog_actions start empty

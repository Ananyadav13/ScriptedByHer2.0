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
        Manager(id="mgr_north", name="Priya (North zone)", api_key="bt_live_north_7Kd2Xp9QaR4mZ"),
        Manager(id="mgr_south", name="Arjun (South zone)", api_key="bt_live_south_3Fh8Lm5WcT6nB"),
        Manager(id="mgr_west", name="Rohan (West zone)", api_key="bt_live_west_9Jq1Vs7YbN2xE"),
    ])

    # ---------- SELLERS (manager_id links each to a business manager) ----------
    # A spread of ratings + trust profiles so the manager/catalog views have real depth.
    sellers = [
        # --- scenario sellers (load-bearing IDs) ---
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
        Seller(id="seller_knockoff", name="StreetStyle Optics", rating=4.2,
               account_created_at=_dt(450), trust_flags=[], manager_id="mgr_north"),
        # --- depth sellers (varied ratings / fraud levels) ---
        Seller(id="seller_gadgets", name="TechBazaar", rating=4.6,
               account_created_at=_dt(1100), trust_flags=[], manager_id="mgr_south"),
        Seller(id="seller_beauty", name="GlowUp Cosmetics", rating=4.3,
               account_created_at=_dt(700), trust_flags=[], manager_id="mgr_west"),
        Seller(id="seller_scam", name="MegaDiscount Hub", rating=1.4,
               account_created_at=_dt(15), trust_flags=["new_account_cluster", "quality_complaints"],
               case_count=8, manager_id="mgr_west"),  # serial fraudster -> ban
        Seller(id="seller_kids", name="LittleStars Kids", rating=4.5,
               account_created_at=_dt(820), trust_flags=[], manager_id="mgr_west"),
        Seller(id="seller_jewelry", name="ShineOn Jewels", rating=2.1,
               account_created_at=_dt(260), trust_flags=["quality_complaints"],
               case_count=3, manager_id="mgr_north"),
        Seller(id="seller_saree", name="SilkTradition", rating=4.0,
               account_created_at=_dt(540), trust_flags=[], manager_id="mgr_south"),
        Seller(id="seller_mobile", name="SmartWorld Mobiles", rating=3.5,
               account_created_at=_dt(330), trust_flags=[], manager_id="mgr_west"),
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
        # --- depth catalog (varied sellers / ratings / issues) ---
        Product(id="prod_gadget_powerbank", seller_id="seller_gadgets",
                title="20000mAh Fast-Charging Power Bank", brand="TechBazaar", category="electronics",
                price=1199, mrp=2499, images=["powerbank.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_gadget_earphones", seller_id="seller_gadgets",
                title="Wireless Bluetooth Earphones (40h)", brand="TechBazaar", category="electronics",
                price=899, mrp=1999, images=["earphones2.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_beauty_serum", seller_id="seller_beauty",
                title="Vitamin C Face Serum 30ml", brand="GlowUp", category="beauty",
                price=349, mrp=799, images=["serum.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_beauty_lipstick", seller_id="seller_beauty",
                title="Matte Liquid Lipstick Set of 5", brand="GlowUp", category="beauty",
                price=449, mrp=1199, images=["lipstick.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_kids_tshirt", seller_id="seller_kids",
                title="Kids Cartoon Print T-Shirt (Cotton)", brand="LittleStars", category="apparel",
                price=299, mrp=699, images=["kids.jpg"], fabric_claim="cotton", status="active",
                size_chart_json=None),  # missing size chart -> Agent-2 flag
        Product(id="prod_saree_silk", seller_id="seller_saree",
                title="Banarasi Silk Saree with Blouse", brand="SilkTradition", category="apparel",
                price=12999, mrp=24999, images=["saree.jpg"], fabric_claim="pure silk", status="active",
                size_chart_json={"Free Size": "5.5m saree + 0.8m blouse"}),
        Product(id="prod_mobile_case", seller_id="seller_mobile",
                title="Shockproof Phone Back Cover", brand="SmartWorld", category="electronics",
                price=199, mrp=499, images=["case.jpg"], fabric_claim=None, status="active"),
        # already handled by Agent 2: quality-complaint cluster -> held for info (needs QC)
        Product(id="prod_jewelry_necklace", seller_id="seller_jewelry",
                title="Gold-Plated Kundan Necklace Set", brand="ShineOn", category="accessories",
                price=699, mrp=2499, images=["necklace.jpg"], fabric_claim=None, status="needs_info"),
        # already handled by Agent 1: a second counterfeit (branded watch far below MRP) -> LOCKED
        Product(id="prod_scam_watch", seller_id="seller_scam",
                title="Luxury Chronograph Watch (Branded)", brand="Omega", category="watches",
                price=799, mrp=450000, images=["scamwatch.jpg"], fabric_claim=None, status="locked"),
        # already handled by Agent 2: fraud-review cluster -> SUSPENDED
        Product(id="prod_scam_perfume", seller_id="seller_scam",
                title="Imported Luxury Perfume 100ml", brand="MegaDiscount", category="beauty",
                price=299, mrp=4999, images=["perfume.jpg"], fabric_claim=None, status="suspended"),
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
    # viral honest: a GENUINELY viral product — 11k+ real buyers, 4.7★, growth spread
    # over ~90 days from OLD/established accounts. High volume + high rating + NO
    # new-account burst is exactly the honest-viral pattern Agent 1 must clear.
    vi_txt = [
        "Great fit, soft cotton, went viral on reels!",
        "So comfy, perfect for summer 👌",
        "Love the oversized fit, true to size",
        "Fabric is really soft, totally worth it",
        "Trendy and comfortable, highly recommend",
        "Ordered 3 more for the family, superb",
        "Colour didn't fade after wash, happy",
    ]
    for i in range(11200):
        # ~4.8 avg: 80% five-star, 15% four, 5% three
        r = 5 if i % 20 < 16 else (4 if i % 20 < 19 else 3)
        reviews.append(Review(id=f"rev_vi_{i}", product_id="prod_viral_honest",
                              rating=r, text=vi_txt[i % len(vi_txt)],
                              created_at=_dt(1 + i % 90), reviewer_account_age_days=300 + (i % 900)))
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

    # ---- depth-catalog reviews (varied, established accounts unless noted) ----
    pos = ["Great product, value for money", "Works perfectly, very happy",
           "Good quality, exactly as described", "Fast delivery, nice packaging",
           "Just what I wanted, recommend"]
    beauty_pos = ["Skin feels great, will reorder", "Genuine product, good results",
                  "Lovely shades, long lasting", "Worth the price, authentic", "Absolutely loved it!"]
    def _add(pid, sid, n, rating_fn, texts, age0, age_step=8, day_mod=40, day0=0, age=None):
        for i in range(n):
            reviews.append(Review(
                id=f"rev_{sid}_{i}", product_id=pid, rating=rating_fn(i),
                text=texts[i % len(texts)], created_at=_dt(day0 + i % day_mod),
                reviewer_account_age_days=(age if age is not None else age0 + i * age_step)))
    _add("prod_gadget_powerbank", "pb", 42, lambda i: 5 if i % 5 else 4, pos, 250)
    _add("prod_gadget_earphones", "ep", 31, lambda i: 5 if i % 4 else 4, pos, 300, 7)
    _add("prod_beauty_serum", "bs", 26, lambda i: 5 if i % 5 else 4, beauty_pos, 200, 10)
    _add("prod_beauty_lipstick", "bl", 21, lambda i: 5 if i % 4 else 4, beauty_pos, 220, 9)
    _add("prod_kids_tshirt", "kd", 18, lambda i: 4 if i % 3 else 5,
         ["Soft cotton, kids love it", "Good fit for my 4yr old", "Nice print, washes well",
          "Size ran a bit small", "Cute and comfortable"], 260, 12)
    _add("prod_saree_silk", "sr", 22, lambda i: 4 if i % 2 else 5,
         ["Beautiful saree, rich look", "Silk quality is good", "Loved the colour",
          "Perfect for functions", "Slight colour variation but ok"], 280, 11)
    _add("prod_mobile_case", "mc", 16, lambda i: 3 if i % 2 else 4,
         ["Decent cover, fits well", "Ok for the price", "Average quality",
          "Protects the phone fine", "Buttons a bit stiff"], 180, 9, day_mod=50)
    # jewelry: quality-complaint cluster -> Agent-2 correction/suspend candidate
    _add("prod_jewelry_necklace", "jw", 700, lambda i: 2 if i % 5 else 1,
         ["Gold plating faded in a week", "Turned black quickly, poor quality",
          "Looks cheap, not as pictured", "A stone fell off after one use"],
         0, day_mod=55, age=240)
    # scam watch: counterfeit burst (5-star from brand-new accounts, ₹799 'Omega')
    _add("prod_scam_watch", "sw", 14, lambda i: 5,
         ["Best Omega copy, looks real!", "Amazing luxury watch so cheap",
          "Genuine branded piece, wow", "Original quality, superb"], 0, day0=2, age=3)
    # scam perfume: fraud cluster -> suspend candidate
    _add("prod_scam_perfume", "sp", 600, lambda i: 1,
         ["Fake, smells like spirit", "Not original, cheap knockoff",
          "Scam product, totally avoid", "Nothing like the brand claimed"],
         0, day_mod=50, age=150)
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
    # order volume for the second counterfeit ('Omega' watch) so it too clears the floor
    for i in range(22):
        orders.append(Order(id=f"order_sw_{i}", buyer_id="buyer_normal",
                            product_id="prod_scam_watch", hub_id="hub_normal",
                            otp_scan_count=1, items_count=1, delivered_at=_dt(5 + i % 20),
                            hub_anomaly_flag=False, geo_photo_verified=True, status="delivered"))
    db.add_all(orders)

    # ---------- SIZE DRIFT ----------
    db.add_all([
        SizeDrift(brand="StepUp", category="footwear", label_size="8",
                  true_measurement_delta=-1.0, sample_size=214),  # runs 1 size small
    ])

    # ---------- NOTIFICATIONS (role-wise inbox: seller / manager / buyer) ----------
    from .models import Notification

    def _ntf(nid, audience, recipient, subject, body, priority="normal", related=None, days=1):
        return Notification(id=nid, audience=audience, recipient_id=recipient, subject=subject,
                            body=body, priority=priority, related_id=related, created_at=_dt(days))

    db.add_all([
        # --- SELLER inbox: what action was taken / what's needed ---
        _ntf("ntf_s1", "seller", "seller_lowrated", "Listing suspended",
             "‘Wireless Earbuds Pro Max’ was suspended after a fraud/quality complaint cluster. "
             "Contact your manager to appeal.", "immediate", "prod_lowrated_fraud"),
        _ntf("ntf_s2", "seller", "seller_fixable", "Action needed: add a size chart",
             "‘Cotton Bedsheet Double’ is in a correction window — add measurements to go back to full visibility.",
             "high", "prod_fixable_bedsheet"),
        _ntf("ntf_s3", "seller", "seller_kids", "Action needed: add a size chart",
             "‘Kids Cartoon Print T-Shirt’ is live but missing a size chart. Add one to reduce returns.",
             "normal", "prod_kids_tshirt"),
        _ntf("ntf_s4", "seller", "seller_jewelry", "Quality complaints rising",
             "‘Gold-Plated Kundan Necklace’ has a growing ‘plating fades’ complaint cluster. Review your QC.",
             "high", "prod_jewelry_necklace"),
        _ntf("ntf_s5", "seller", "seller_scam", "Multiple listings under review",
             "Two of your listings match a counterfeit/fraud pattern and are pending manager review.",
             "immediate", "prod_scam_watch"),
        _ntf("ntf_s6", "seller", "seller_counterfeit", "Listing locked for authenticity",
             "‘Rolex Submariner Watch’ was locked (price far below MRP + new-account review burst). "
             "Submit a quality-check video to appeal.", "immediate", "prod_counterfeit_rolex"),
        # --- MANAGER inbox: what's in my queue ---
        _ntf("ntf_m1", "manager", "mgr_north", "3 listings need your decision",
             "Priya, your queue has locks/holds awaiting sign-off (counterfeit, jewelry quality, knockoff).",
             "high"),
        _ntf("ntf_m2", "manager", "mgr_south", "Correction window opened",
             "Arjun, HomeComfort’s bedsheet entered a correction window — a size-chart fix is drafted.",
             "normal", "prod_fixable_bedsheet"),
        _ntf("ntf_m3", "manager", "mgr_west", "Fraud pattern detected",
             "Rohan, ‘MegaDiscount Hub’ (15-day-old, 8 cases) has two fraud-flagged listings. Consider a ban.",
             "immediate"),
        # --- BUYER inbox: transparency + safety ---
        _ntf("ntf_b1", "buyer", "buyer_normal", "A listing you viewed was locked",
             "The ‘Rolex Submariner Watch’ you viewed was locked for authenticity concerns. "
             "Here are verified alternatives from trusted sellers.", "high", "prod_counterfeit_rolex"),
        _ntf("ntf_b2", "buyer", "buyer_normal", "Your size was auto-adjusted",
             "For StepUp footwear we suggested size 9 (you usually take 8) — this brand runs 1 size small.",
             "normal", "prod_size_shoes"),
        _ntf("ntf_b3", "buyer", "buyer_normal", "Refund fast-tracked",
             "Your delivery dispute was corroborated by two independent signals — refund is on the way.",
             "normal", "order_otp_dispute"),
    ])

    # ---------- SEEDED HISTORY: past cases the agents already resolved ----------
    # Gives the Agent-1 "cases resolved" view and the manager queue real content on
    # first load (the scenario products — rolex/kurti/viral — stay ACTIVE for live demos).
    def _inv(iid, product_id, order_id, trigger, decision, action, conf, evidence, expl, days):
        return Investigation(
            id=iid, product_id=product_id, order_id=order_id, trigger=trigger, status="done",
            tool_calls_log_json=[], created_at=_dt(days),
            verdict_json={"decision": decision, "action": action, "confidence": conf,
                          "evidence": evidence, "buyer_explanation": expl,
                          "recommended_action": "", "suggested_remedy": ""})

    db.add_all([
        _inv("inv_h1", "prod_scam_watch", None, "pre_purchase", "counterfeit_lock", "lock", 0.98,
             ["'Omega' priced at 0.18% of MRP (< 35%)", "14 five-star reviews, 100% from 3-day-old accounts",
              "seller MegaDiscount Hub is 15 days old with 8 open cases"],
             "This branded watch was locked — the price and review pattern indicate a counterfeit.", 2),
        _inv("inv_h2", "prod_size_shoes", "order_otp_dispute", "post_delivery", "refund_fast_track", "refund", 0.95,
             ["1 OTP scanned for 3 items", "delivered via a flagged hub (6 cases)", "no geo-verified photo"],
             "Two independent signals corroborated the dispute — refund fast-tracked.", 1),
        _inv("inv_h3", "prod_viral_honest", None, "tripwire", "cleared", "none", 0.93,
             ["review spike but 0% from new accounts", "seller 900 days old, rating 4.4"],
             "A volume spike from genuine aged accounts — a real viral seller, not fraud. Cleared.", 3),
        _inv("inv_h4", "prod_fabric_kurti", "order_fabric_dispute", "post_delivery", "recommend_review", "route_manager_review", 0.62,
             ["material claim 'pure cotton' disputed", "negative fabric-complaint cluster"],
             "Uncertain media evidence — recommended to a human manager rather than auto-acting.", 4),
        _inv("inv_h5", "prod_fabric_kurti", "order_serial", "post_delivery", "manual_review", "route_manual_review", 0.7,
             ["buyer has 7 prior claims (>= 5) -> serial-claimer pattern"],
             "Routed to manual review — the claimant has a serial-claim history.", 5),
        _inv("inv_h6", "prod_jewelry_necklace", None, "tripwire", "hold_pending_fix", "hold", 0.8,
             ["quality-complaint cluster: gold plating fades", "trustworthy rating fell below 3.0"],
             "Held pending seller quality-check after a plating-quality complaint cluster.", 2),
    ])

    # catalog actions so locked/held/suspended listings show WHY + populate the manager queue
    def _act(aid, product_id, action, decision, evidence, days):
        return CatalogAction(id=aid, product_id=product_id, action=action,
                             evidence_json={"decision": decision, "evidence": evidence},
                             seller_approved=False, created_at=_dt(days))

    db.add_all([
        _act("act_h1", "prod_scam_watch", "lock", "counterfeit_lock",
             ["price 0.18% of MRP", "5-star burst from 3-day accounts"], 2),
        _act("act_h2", "prod_jewelry_necklace", "hold", "hold_pending_fix",
             ["gold-plating quality complaints", "trustworthy rating < 3.0"], 2),
        _act("act_h3", "prod_scam_perfume", "suspend", "delist_suspend",
             ["fraud-review cluster (600 x 1-star)", "seller flagged, 8 cases"], 2),
    ])

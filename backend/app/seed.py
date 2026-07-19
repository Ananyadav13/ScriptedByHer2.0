"""Seed the demo catalog and golden-path scenarios. Idempotent: drops + recreates in dev.

Stable IDs are load-bearing — frontend scenario buttons and later phases reference them.
"""
from copy import deepcopy
from datetime import datetime, timedelta

from .db import Base, SessionLocal, engine
from .models import (
    Buyer,
    CatalogAction,
    Hub,
    Investigation,
    Manager,
    Notification,
    Order,
    Product,
    ProductVariant,
    Review,
    Seller,
    SizeDrift,
)
from .time_utils import utcnow

NOW = utcnow()

# ---------------------------------------------------------------------------
# Seeded quality fingerprints — the "golden fields" a listing video distils into.
#
# Defined here as a named constant rather than inline, because two callers need the exact
# same values: the seeder below, and `routers/media.py`'s reset endpoint, which restores
# this after a live extraction so the presenter can re-run the demo from a known state.
# One definition means the restored state is the seeded state by construction.
#
# These are PRE-EXTRACTED so the flagship comparison is byte-identical on every run and
# costs zero Gemini quota. `POST /products/{id}/listing-video` replaces them with a real
# live extraction from an uploaded clip; the reset endpoint puts them back.
# ---------------------------------------------------------------------------
SEEDED_FINGERPRINTS: dict[str, dict] = {
    "prod_fabric_kurti": {
        "listing_video_path": "kurti_listing_black.mp4",
        "fingerprint": {
            "attributes": {
                "weave_structure": "woven, medium plain weave",
                "surface_sheen": "semi-matte",
                "fibre_texture": "smooth, soft",
                "opacity": "opaque",
                "stitch_quality": "dense, even seams",
                "drape": "structured, holds shape",
                "embellishment_type": "thread embroidery yoke",
                "colour": "black", "shade": "jet black", "print_colourway": "white on black",
            },
            "summary": "Opaque, semi-matte woven rayon anarkali with an embroidered yoke — the Black variant.",
            "confidence": 0.86,
            "notes": ["listing video shows the Black colourway only"],
            "source_frames": 6,
        },
    },
}


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
        Manager(id="mgr_west", name="Rohan (West zone)"),
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
        Seller(id="seller_mobile", name="SmartWorld Mobiles", rating=3.5,
               account_created_at=_dt(330), trust_flags=[], manager_id="mgr_west"),
        # good seller whose bag listing carries a MEASUREMENT gap (not a fraud problem).
        # Under mgr_north so the seller-journey walkthrough shows this seller + EthnicWeave
        # (the kurti) in one manager view.
        Seller(id="seller_bags", name="Aaraals Collection", rating=4.0,
               account_created_at=_dt(610), trust_flags=[], manager_id="mgr_north"),
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
                title="Checked Cotton Casual Shirt (Viral)", brand="TrendyThreads", category="apparel",
                price=251, mrp=278, images=["tshirt_real.jpg"],
                fabric_claim="100% cotton", status="active",
                size_chart_json={"M": "38", "L": "40", "XL": "42", "XXL": "44"}),
        # 3. Fabric mismatch: claims cotton, reviews say synthetic (hybrid media).
        #    Sold in 3 colourways but the seller filmed ONE listing video (the Black variant).
        #    quality_fingerprint_json = the variant-invariant "golden fields" distilled from
        #    that video, so a dispute on the BLUE variant is judged on weave/sheen/texture,
        #    NOT on colour (which would false-flag the honest seller). Pre-seeded here so the
        #    cross-variant demo works with zero LLM quota; a real recording dropped into
        #    media/videos/ + a cleared fingerprint would re-extract it live.
        Product(id="prod_fabric_kurti", seller_id="seller_kurti",
                title="Rayon Embroidered Anarkali Kurti", brand="EthnicWeave", category="apparel",
                price=384, mrp=426, images=["kurti.jpg"],
                fabric_claim="rayon", status="active",
                listing_video_path=SEEDED_FINGERPRINTS["prod_fabric_kurti"]["listing_video_path"],
                # frames sampled from the seller's listing video (the BLACK variant they filmed) —
                # the buyer's real photos live in frontend/public/evidence/.
                listing_frame_urls=["/evidence/kurti_listing_1.png", "/evidence/kurti_listing_2.png",
                                    "/evidence/kurti_listing_3.png"],
                size_chart_json={"S": "36", "M": "38", "L": "40"},
                # golden fields distilled from the listing video: opaque, semi-matte woven RAYON.
                # deep-copied: the ORM would otherwise hold a reference to the module
                # constant, and a later mutation would silently rewrite the seed itself.
                quality_fingerprint_json=deepcopy(SEEDED_FINGERPRINTS["prod_fabric_kurti"]["fingerprint"])),
        # 4. Size drift: brand runs small. FLAGGED as a size-drift case for the manager (advisory
        #    — the sale continues); the buyer already gets the Agent-2 size hint in the cart.
        Product(id="prod_size_shoes", seller_id="seller_shoes",
                title="Running Shoes - Lightweight", brand="StepUp", category="footwear",
                price=1299, mrp=1599, images=["shoes.jpg"],
                fabric_claim=None, status="flagged",
                size_chart_json={"7": "UK7", "8": "UK8", "9": "UK9"}),
        # 5. Low-rated fraud cluster -> already SUSPENDED by Agent 2 (fraud reviews, repeat-offender
        #    seller). Pre-resolved so the manager queue shows a real suspension on first load, not
        #    an egregious 1-star/1000-review listing sitting "active".
        Product(id="prod_lowrated_fraud", seller_id="seller_lowrated",
                title="Wireless Neckband Earphones", brand="BargainBin", category="electronics",
                price=699, mrp=899, images=["earbuds.jpg"],
                fabric_claim=None, status="suspended"),
        # 6. Fixable gaps -> in a CORRECTION WINDOW (missing size chart, dominant size complaint).
        #    Pre-resolved with a drafted fix waiting for the seller to approve (see seed actions).
        Product(id="prod_fixable_bedsheet", seller_id="seller_fixable",
                title="Cotton Bedsheet Double", brand="HomeComfort", category="home",
                price=549, mrp=699, images=["bedsheet.jpg"],
                fabric_claim="cotton", status="correction_window",
                size_chart_json=None),
        # 6b. Delivery-fault: a GOOD seller's product ruined by a bad courier -> Agent-2
        #     audit routes to logistics referral, NO seller-rating penalty (fairness rule).
        Product(id="prod_damaged_courier", seller_id="seller_shoes",
                title="Cold-Pressed Juice 1L (Glass Bottle)", brand="StepUp", category="home",
                price=299, mrp=379, images=["bottle.jpg"], fabric_claim=None, status="active"),
        # 7. Loved knockoff: branded-style, far below MRP (counterfeit signal) BUT
        #    genuinely high trustworthy rating -> relabel_required, NOT a ban.
        Product(id="prod_knockoff_loved", seller_id="seller_knockoff",
                title="Aviator Sunglasses (Rayban-inspired)", brand="Rayban", category="accessories",
                price=499, mrp=7999, images=["aviator.jpg"],
                fabric_claim=None, status="active",
                # real measurements: this listing's problem is the BRAND claim, not the spec —
                # keep the measurement gap unique to prod_bag_combo.
                size_chart_json={"Free Size": "Lens 58mm x Bridge 14mm x Temple 140mm"}),
        # benign filler (realistic catalog, no flags)
        Product(id="prod_normal_mug", seller_id="seller_viral",
                title="Ceramic Coffee Mug 350ml", brand="TrendyThreads", category="home",
                price=199, mrp=249, images=["mug.jpg"], fabric_claim="Ceramic", status="active"),
        # --- depth catalog (varied sellers / ratings / issues) ---
        Product(id="prod_gadget_powerbank", seller_id="seller_gadgets",
                title="Wireless Charging Pad 15W", brand="TechBazaar", category="electronics",
                price=1199, mrp=1499, images=["powerbank.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_gadget_earphones", seller_id="seller_gadgets",
                title="Wireless Neckband Earphones (40h)", brand="TechBazaar", category="electronics",
                price=899, mrp=1099, images=["earphones2.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_beauty_serum", seller_id="seller_beauty",
                title="Men's Face Moisturizer 200ml", brand="GlowUp", category="beauty",
                price=349, mrp=449, images=["serum.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_beauty_lipstick", seller_id="seller_beauty",
                title="Matte Liquid Lipstick Set of 5", brand="GlowUp", category="beauty",
                price=449, mrp=549, images=["lipstick.jpg"], fabric_claim=None, status="active"),
        Product(id="prod_kids_tshirt", seller_id="seller_kids",
                title="Kids Polka-Dot Cotton Dress", brand="LittleStars", category="apparel",
                price=299, mrp=349, images=["kids.jpg"], fabric_claim="cotton", status="active",
                size_chart_json=None),  # missing size chart -> Agent-2 flag
        Product(id="prod_mobile_case", seller_id="seller_mobile",
                title="Shockproof Phone Back Cover", brand="SmartWorld", category="electronics",
                price=199, mrp=249, images=["case.jpg"], fabric_claim=None, status="active"),
        # MEASUREMENT GAP: a genuinely good bag (4.0★, honest seller) sold as "Free Size" with
        # NO dimensions. Buyers can't tell how big it is, so a steady size-complaint minority
        # runs through otherwise-happy reviews ("good quality but small size"). Nothing here is
        # fraud — the fix is a spec, not a ban: the mandatory-fields gate asks for L x W x H.
        # The vacuous {"Free Size": "Free Size"} chart is the defect itself, not an oversight.
        Product(id="prod_bag_combo", seller_id="seller_bags",
                title="Women's Handbag Combo - Tote, Sling & Purse (Pack of 4)",
                brand="Aaraals", category="accessories",
                price=325, mrp=399, images=["bag_combo.jpg"], fabric_claim="PU Leather",
                # HELD for info: the size-complaint cluster + vacuous "Free Size" chart tripped
                # the mandatory-fields gate. A dimensions fix is drafted (see seed actions) and
                # waits for the seller — the remedy is a spec, not a suspension.
                status="needs_info", size_chart_json={"Free Size": "Free Size"}),
        # already handled by Agent 2: quality-complaint cluster -> held for info (needs QC)
        # priced like a real Meesho jewellery set (₹235) — at the old ₹699/₹2499 it read as
        # 28% of MRP and tripped the counterfeit PRICE signal, which was a false positive.
        Product(id="prod_jewelry_necklace", seller_id="seller_jewelry",
                title="Gold-Plated Kundan Necklace Set", brand="ShineOn", category="accessories",
                price=235, mrp=499, images=["necklace.jpg"], fabric_claim=None, status="needs_info",
                size_chart_json={"Free Size": "Necklace 42cm + earrings 4cm"}),
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
    for i in range(160):  # a big FAKE burst — the tell is that every account is 2–4 days old
        reviews.append(Review(id=f"rev_cf_{i}", product_id="prod_counterfeit_rolex",
                              rating=5, text=cf_txt[i % len(cf_txt)], created_at=_dt(1 + i % 3),
                              reviewer_account_age_days=2 + i % 3))
    # viral honest: a GENUINELY viral product — ~2.4k real buyers, 4.7★, growth spread
    # over ~90 days from OLD/established accounts. Still clearly the catalogue's top seller
    # (~4x the next product) without the cartoonish 11k. High volume + high rating + NO
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
    for i in range(2400):
        # ~4.8 avg: 80% five-star, 15% four, 5% three
        r = 5 if i % 20 < 16 else (4 if i % 20 < 19 else 3)
        reviews.append(Review(id=f"rev_vi_{i}", product_id="prod_viral_honest",
                              rating=r, text=vi_txt[i % len(vi_txt)],
                              created_at=_dt(1 + i % 90), reviewer_account_age_days=300 + (i % 900)))
    # fabric kurti: negative cluster; two reviews carry videos (vision path).
    # video_path points at a REAL review-video asset dropped into media/videos/
    # (or a frames/<dir> of stills). Left None until the physical recordings are
    # supplied; the vision tool then reports available=False and the agent decides
    # on the text signals alone — no fabricated evidence. Wire the filenames here.
    KURTI_VIDEO = {0: None, 3: None}  # e.g. {0: "kurti_review_synthetic_1.mp4", 3: "kurti_review_2.mp4"}
    kurti_neg = [
        ("Transparent material, feels like crepe not rayon", 2),
        ("See-through fabric, had to wear a slip under it", 2),
        ("Shiny and thin, not the rayon shown in the listing", 1),
        ("Cloth is sheer and slippery, misleading listing", 2),
        ("Not the opaque rayon promised — disappointed", 2),
    ]
    for i, (t, r) in enumerate(kurti_neg):
        vpath = KURTI_VIDEO.get(i)
        reviews.append(Review(id=f"rev_ku_{i}", product_id="prod_fabric_kurti",
                              rating=r, text=t, created_at=_dt(10 + i),
                              reviewer_account_age_days=300,
                              has_video=(i in KURTI_VIDEO), video_path=vpath))
    # ...plus a realistic base of reviews (a popular kurti has hundreds) — a strong
    # fabric-complaint minority within the negatives keeps the advisory story intact.
    ku_pos = ["Lovely kurti, good stitching", "Nice for daily wear", "Colour is pretty",
              "Comfortable and value for money", "Fits well, happy with it"]
    ku_neg = ["Fabric feels synthetic, not cotton", "Not pure cotton as claimed",
              "Material is thin and shiny", "Shrank a little after wash"]
    for i in range(330):
        reviews.append(Review(id=f"rev_kup_{i}", product_id="prod_fabric_kurti",
                              rating=5 if i % 3 else 4, text=ku_pos[i % 5],
                              created_at=_dt(2 + i % 80), reviewer_account_age_days=280 + i % 400))
    for i in range(55):  # the fabric-mismatch cluster (dominant NEGATIVE) -> advisory review
        reviews.append(Review(id=f"rev_kun_{i}", product_id="prod_fabric_kurti",
                              rating=2 if i % 4 else 1, text=ku_neg[i % 4],
                              created_at=_dt(2 + i % 60), reviewer_account_age_days=290))
    # bag combo: a GOOD product with a LISTING gap. The praise is real (build quality, price)
    # and the seller is honest, so the trustworthy rating stays ~3.8 and NO delist tier trips.
    # The recurring complaint is purely dimensional — buyers expected a bigger bag because the
    # listing only ever said "Free Size". This is the case the mandatory-fields gate exists for:
    # the remedy is measurements, not a suspension.
    bag_pos = ["Good quality bag, worth the price", "Nice combo, all 4 pieces are useful",
               "Stitching is neat, looks premium", "Colour exactly as shown, happy",
               "Great value for a pack of 4"]
    bag_size = ["Good quality but small size", "Bag is much smaller than it looks in the photo",
                "Size not mentioned anywhere, turned out tiny", "Cute but too small for daily use",
                "No measurements given, expected a bigger tote",
                "Quality is fine, just smaller than I imagined"]
    for i in range(210):
        reviews.append(Review(id=f"rev_bag_{i}", product_id="prod_bag_combo",
                              rating=5 if i % 3 else 4, text=bag_pos[i % 5],
                              created_at=_dt(2 + i % 70), reviewer_account_age_days=260 + i % 500))
    for i in range(90):  # the size-complaint minority -> 'missing_measurements' + size_issue
        reviews.append(Review(id=f"rev_bagsz_{i}", product_id="prod_bag_combo",
                              rating=2 if i % 3 else 1, text=bag_size[i % 6],
                              created_at=_dt(2 + i % 65), reviewer_account_age_days=270 + i % 300))
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
    for i in range(480):
        reviews.append(Review(id=f"rev_kn_{i}", product_id="prod_knockoff_loved",
                              rating=5 if i % 5 else 4, text=knock_txt[i % 5],
                              created_at=_dt(i % 120), reviewer_account_age_days=200 + i % 700))
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
    _add("prod_gadget_powerbank", "pb", 620, lambda i: 5 if i % 5 else 4, pos, 250, 1, day_mod=80)
    _add("prod_gadget_earphones", "ep", 430, lambda i: 5 if i % 4 else 4, pos, 300, 1, day_mod=75)
    _add("prod_beauty_serum", "bs", 540, lambda i: 5 if i % 5 else 4, beauty_pos, 200, 1, day_mod=70)
    _add("prod_beauty_lipstick", "bl", 360, lambda i: 5 if i % 4 else 4, beauty_pos, 220, 1, day_mod=70)
    _add("prod_kids_tshirt", "kd", 310, lambda i: 4 if i % 3 else 5,
         ["Soft cotton, kids love it", "Good fit for my 4yr old", "Nice print, washes well",
          "Size ran a bit small", "Cute and comfortable"], 260, 1, day_mod=75)
    _add("prod_mobile_case", "mc", 200, lambda i: 3 if i % 2 else 4,
         ["Decent cover, fits well", "Ok for the price", "Average quality",
          "Protects the phone fine", "Buttons a bit stiff"], 180, 1, day_mod=60)
    _add("prod_size_shoes", "sh", 460, lambda i: 5 if i % 3 else 4,
         ["Super comfy, great for running", "True to size once adjusted", "Lightweight and durable",
          "Good grip, value for money", "Nice colour, fits well"], 250, 1, day_mod=85)
    _add("prod_normal_mug", "mg", 180, lambda i: 5 if i % 4 else 4,
         ["Sturdy mug, nice finish", "Good size for chai", "Microwave safe, happy",
          "Value for money", "Colour as shown"], 200, 1, day_mod=60)
    # jewelry: quality-complaint cluster -> Agent-2 correction/suspend candidate
    _add("prod_jewelry_necklace", "jw", 700, lambda i: 2 if i % 5 else 1,
         ["Gold plating faded in a week", "Turned black quickly, poor quality",
          "Looks cheap, not as pictured", "A stone fell off after one use"],
         0, day_mod=55, age=240)
    # scam watch: counterfeit burst (5-star from brand-new accounts, ₹799 'Omega')
    _add("prod_scam_watch", "sw", 130, lambda i: 5,
         ["Best Omega copy, looks real!", "Amazing luxury watch so cheap",
          "Genuine branded piece, wow", "Original quality, superb"], 0, day0=1, day_mod=3, age=3)
    # scam perfume: fraud cluster -> suspend candidate
    _add("prod_scam_perfume", "sp", 600, lambda i: 1,
         ["Fake, smells like spirit", "Not original, cheap knockoff",
          "Scam product, totally avoid", "Nothing like the brand claimed"],
         0, day_mod=50, age=150)
    db.add_all(reviews)

    # ---- ratings_total: star ratings INCLUDING rating-only (no text) submissions ----
    # Real listings carry ~3x more ratings than written reviews (7470/2425, 59385/20506,
    # 11810/4218 all land near 2.9-3.1x), so the two numbers must differ on screen. The
    # multiplier is deterministic per product id — same catalogue every reseed.
    _counts: dict[str, int] = {}
    for r in reviews:
        _counts[r.product_id] = _counts.get(r.product_id, 0) + 1
    for p in products:
        n = _counts.get(p.id, 0)
        # 2.8x-3.1x, varied per product so the catalogue doesn't read as one formula
        p.ratings_total = round(n * (2.8 + (sum(map(ord, p.id)) % 4) / 10)) if n else 0

    # ---------- PRODUCT VARIANTS (colourways) ----------
    # The kurti is sold in 3 colours; the seller filmed the BLACK one (is_listing_reference).
    # The fabric-dispute order below ships the BLUE variant -> a CROSS-VARIANT media check,
    # the exact case that must NOT be false-flagged on colour.
    db.add_all([
        ProductVariant(id="var_kurti_black", product_id="prod_fabric_kurti", name="Black",
                       colour="black", images=["kurti.jpg"], is_listing_reference=True),
        ProductVariant(id="var_kurti_blue", product_id="prod_fabric_kurti", name="Blue",
                       colour="blue", images=["kurti.jpg"]),
        ProductVariant(id="var_kurti_red", product_id="prod_fabric_kurti", name="Red",
                       colour="red", images=["kurti.jpg"]),
    ])

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
    # Three DISTINCT fraud/complaint scenarios, each on its own product so they don't blur:
    #   1. GENUINE complaint  — buyer_normal, kurti fabric mismatch  -> manager upholds, refund
    #   2. REPEAT-CLAIM fraud  — serial claimer, a CLEAN serum       -> manual review, manager rejects
    #   3. HUB / OTP fraud     — buyer_normal, a powerbank           -> refund fast-track + hub escalation
    orders = [
        # 2. REPEAT CLAIMANT: a well-rated serum, correctly described + delivered (no real issue).
        #    The serial claimer (7 prior claims) files anyway -> routed to MANUAL REVIEW so the
        #    manager can reject the fraudulent refund. Pre-set to manual_review so it shows on load.
        Order(id="order_serial", buyer_id="buyer_serial_claimer", product_id="prod_beauty_serum",
              claim_type="item_not_as_described",
              hub_id="hub_normal", otp_scan_count=1, items_count=1, delivered_at=_dt(2),
              hub_anomaly_flag=False, geo_photo_verified=True, status="manual_review"),
        # 3. HUB / OTP FRAUD: 3 items ordered, only 1 OTP scanned, routed via the FAULTY hub with
        #    no geo-photo -> two independent signals -> refund fast-track + immediate hub escalation.
        Order(id="order_otp_dispute", buyer_id="buyer_normal", product_id="prod_gadget_powerbank",
              hub_id="hub_faulty", otp_scan_count=1, items_count=3, delivered_at=_dt(1),
              hub_anomaly_flag=True, geo_photo_verified=False, status="delivered"),
        # 1. clean buyer, material dispute ("received synthetic, not cotton") on the BLUE variant,
        # WITH photo/video evidence. The listing video shows BLACK -> a cross-variant media
        # check: the quality-fingerprint diff must ignore colour and judge only weave/sheen/
        # texture -> ADVISORY recommend_review to the manager, NOT a colour false-flag.
        # buyer_evidence_json holds media paths; left empty until real buyer media is supplied
        # (the fingerprint diff then reports "not comparable" rather than fabricating a verdict).
        Order(id="order_fabric_dispute", buyer_id="buyer_normal", product_id="prod_fabric_kurti",
              variant_id="var_kurti_blue", claim_type="fabric_mismatch",
              hub_id="hub_normal", otp_scan_count=1, items_count=1, delivered_at=_dt(1),
              hub_anomaly_flag=False, geo_photo_verified=True,
              # the buyer's real photos of the BLUE kurti they received (sheer/crepe).
              buyer_evidence_json=["/evidence/kurti_buyer_1.png", "/evidence/kurti_buyer_2.png"],
              # pre-read observed attributes (deterministic demo): the received item is SHEER and
              # GLOSSY — reads as crepe, not the opaque rayon claimed. Colour differs (blue vs the
              # filmed black) but that is IGNORED; opacity + sheen + drape are what diverge.
              buyer_evidence_fingerprint_json={
                  "weave_structure": "woven, loose",
                  "surface_sheen": "glossy",
                  "fibre_texture": "slippery, smooth",
                  "opacity": "semi-sheer, see-through",
                  "stitch_quality": "even seams",
                  "drape": "fluid, clingy",
                  "embellishment_type": "thread embroidery yoke",
                  "colour": "blue", "shade": "teal blue", "print_colourway": "white on blue",
                  "_summary": "Sheer, glossy, fluid fabric that reads as crepe — see-through against the light.",
              },
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
             ["'Omega' priced at 0.18% of MRP (< 35%)", "130 five-star reviews, 100% from 3-day-old accounts",
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
        # pre-resolved Agent-2 outcomes so the manager queue + product pages read as a running
        # marketplace on first load (not everything "active"). Reasons match evaluate_delisting.
        _act("act_h4", "prod_lowrated_fraud", "suspend", "delist_suspend",
             ["fraud/quality cluster (1000 x 1-star, 100% agree)", "repeat-offender seller (5 cases)"], 3),
        _act("act_h5", "prod_fixable_bedsheet", "correction", "correction_window",
             ["dominant complaint: missing size chart", "trustworthy ~2.0 over 1000 reviews"], 3),
        _act("act_h6", "prod_bag_combo", "hold", "needs_info",
             ["listing sold as ‘Free Size’ with NO measurements", "size-complaint cluster (90 reviews)"], 2),
        # size-drift case for the manager (advisory): the shoes run small — buyers get the hint
        # in the cart; the manager can ask the seller to update the sizing.
        _act("act_h7", "prod_size_shoes", "recommend_review", "size_drift",
             ["StepUp footwear runs 1 size small (214 returns)",
              "Agent 2 recommends the seller update the sizing information"], 1),
    ])

    # ---- pre-seeded fix DRAFTS (Agent 2's proposed corrections, awaiting seller approval) ----
    # So the seller "Suggested fixes" console has real before/after content on first load, and
    # the manager sees corrections in flight. Same shape agent2.draft_fix produces at runtime.
    def _draft(aid, product_id, field, cluster, summary, before, after, rationale, days):
        return CatalogAction(
            id=aid, product_id=product_id, action="fix_draft", seller_approved=False,
            created_at=_dt(days),
            evidence_json={"field": field, "cluster": cluster, "summary": summary,
                           "before": before, "after": after, "rationale": rationale})

    db.add_all([
        _draft("draft_bedsheet", "prod_fixable_bedsheet", "size_chart_json", "size_issue",
               "Add the missing size chart buyers keep asking for",
               {"size_chart_json": None},
               {"size_chart_json": {"Single": "60 in x 90 in", "Double": "90 in x 100 in",
                                    "King": "100 in x 108 in"}},
               "Buyers repeatedly report ordering the wrong size — a measurement chart removes the guesswork.", 3),
        _draft("draft_bag", "prod_bag_combo", "size_chart_json", "size_issue",
               "Replace ‘Free Size’ with real bag dimensions",
               {"size_chart_json": {"Free Size": "Free Size"}},
               {"size_chart_json": {"Tote": "L 30cm x W 12cm x H 26cm", "Sling": "L 22cm x W 8cm x H 16cm",
                                    "Purse": "L 19cm x W 3cm x H 10cm"}},
               "The ‘small size’ complaints come from a listing that never stated dimensions — add L x W x H.", 2),
    ])

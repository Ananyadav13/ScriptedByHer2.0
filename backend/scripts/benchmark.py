"""Throughput benchmark for the deterministic decision layer.

The scalability question for this design is not "how fast is the LLM" — the LLM is
called once per investigation, on demand. It is "how much catalog can the
deterministic layer sweep", because Agent 2's audit and Agent 1's always-watching
tripwires run over every listing, continuously, with no model in the path.

Everything measured here lives in `app/services/` and is pure Python: no network,
no database round-trip, no API key. Run:

    python scripts/benchmark.py
"""
from __future__ import annotations

import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import delisting, quality_fingerprint, risk_checks  # noqa: E402
from app.services import rules  # noqa: E402

N = 20_000


@dataclass
class FakeReview:
    rating: int
    created_at: object
    reviewer_account_age_days: int = 400
    text: str = "fabric felt synthetic and thin"
    is_media_derived: bool = False


@dataclass
class FakeProduct:
    id: str = "p1"
    brand: str = "Rolex"
    price: float = 599.0
    mrp: float = 850_000.0
    reviews: list = field(default_factory=list)


def bench(label: str, fn, n: int = N) -> tuple[str, float, float]:
    fn()  # warm
    samples = []
    t0 = time.perf_counter()
    for _ in range(n):
        s = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - s)
    total = time.perf_counter() - t0
    ops = n / total
    p95_us = statistics.quantiles(samples, n=20)[18] * 1e6
    print(f"  {label:<34} {ops:>12,.0f} ops/s   p95 {p95_us:>8.1f} us")
    return label, ops, p95_us


def main() -> None:
    from datetime import datetime, timedelta

    now = datetime.utcnow()   # services compare against naive UTC
    reviews = [
        FakeReview(rating=1 + (i % 5), created_at=now - timedelta(days=i % 200),
                   reviewer_account_age_days=5 if i % 3 == 0 else 400)
        for i in range(200)
    ]
    product = FakeProduct(reviews=reviews)

    listing_fp = {
        "weave_structure": "woven, tight", "surface_sheen": "matte",
        "fibre_texture": "fibrous", "opacity": "opaque",
        "stitch_quality": "dense", "drape": "structured",
        "embellishment_type": "embroidery", "colour": "black",
    }
    buyer_fp = dict(listing_fp, surface_sheen="glossy", opacity="sheer",
                    fibre_texture="smooth", colour="blue")

    print(f"\nDeterministic decision layer — {N:,} iterations each\n")
    results = [
        bench("price vs MRP check", lambda: risk_checks.price_mrp_risk(product)),
        bench("review-burst detection (200 rev)",
              lambda: risk_checks.review_burst_risk(product)),
        bench("trustworthy rating (200 rev)",
              lambda: risk_checks.trustworthy_rating(product)),
        bench("delisting tier evaluation",
              lambda: delisting.delist_tier(3.2, 1200)),
        bench("quality-fingerprint diff",
              lambda: quality_fingerprint.compare_fingerprints(listing_fp, buyer_fp)),
    ]

    slowest = min(r[1] for r in results)
    print(f"\n  Slowest stage: {slowest:,.0f} ops/s")
    print(f"  A full-catalog sweep is bounded by this stage:")
    for size, label in ((1_000_000, "1M listings"), (10_000_000, "10M listings")):
        print(f"    {label:<14} ~{size / slowest:>8.1f} s of single-core CPU")
    print("\n  No LLM, no network, no DB round-trip on any path above.")
    print("  Embarrassingly parallel: listings are independent, so this divides"
          " across cores/workers.\n")


if __name__ == "__main__":
    main()

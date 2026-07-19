"""POST /products/{id}/delist — per-listing removal from the catalogue.

`/audit` sweeps everything and applies every verdict at once; this endpoint applies the same
engine to ONE listing so the Agent-2 console can show dead stock as a reviewable list with an
explicit action. The tests that matter are the refusals: removal has to be a consequence of
the evidence, never a button that works on anything you point it at.
"""
from __future__ import annotations

from app.db import SessionLocal
from app.models import CatalogAction, Product

DEAD = "prod_deadstock_neckband"       # ★1.4 over ~1,550 buyers, repeat-offender seller
HEALTHY = "prod_normal_mug"            # no tier tripped
COURIER = "prod_damaged_courier"       # trips a tier, but the fault is the hub's


def _status(product_id: str) -> str:
    db = SessionLocal()
    try:
        return db.get(Product, product_id).status
    finally:
        db.close()


class TestDelistEndpoint:
    def test_dead_listing_is_removed_with_its_evidence(self, client):
        findings = client.get("/agent2/findings").json()["products"]
        dead = next(p for p in findings if p["product_id"] == DEAD)
        # the console must be able to show WHY without a second request
        assert dead["delist"] is True
        assert dead["recommended_action"] == "suspend"
        assert dead["rating"] is not None and dead["rating"] < 2.0
        assert dead["review_count"] >= 700
        assert dead["tier_label"]

        r = client.post(f"/products/{DEAD}/delist")
        assert r.status_code == 200
        body = r.json()
        assert body["applied"] is True
        assert body["new_status"] == "suspended"
        assert _status(DEAD) == "suspended"

    def test_removal_is_idempotent(self, client):
        """A double-clicked button must not suspend twice or write a second audit row."""
        client.post(f"/products/{DEAD}/delist")
        second = client.post(f"/products/{DEAD}/delist")
        assert second.status_code == 200
        assert second.json()["applied"] is False

        db = SessionLocal()
        try:
            rows = (db.query(CatalogAction)
                    .filter(CatalogAction.product_id == DEAD,
                            CatalogAction.action == "suspend")
                    .count())
        finally:
            db.close()
        assert rows == 1

    def test_healthy_listing_cannot_be_removed(self, client):
        """The guard that stops this being a free-form delete button."""
        r = client.post(f"/products/{HEALTHY}/delist")
        assert r.status_code == 409
        assert "does not trip a delisting tier" in r.json()["detail"]
        assert _status(HEALTHY) != "suspended"

    def test_delivery_fault_is_not_a_listing_removal(self, client):
        """A courier problem must not cost the seller their listing — the fairness rule."""
        r = client.post(f"/products/{COURIER}/delist")
        assert r.status_code == 409
        assert "logistics referral" in r.json()["detail"]
        assert _status(COURIER) != "suspended"

    def test_unknown_product_is_404(self, client):
        assert client.post("/products/prod_nope/delist").status_code == 404


class TestFindingsExposeDelistEvidence:
    def test_every_product_carries_a_delist_verdict(self, client):
        products = client.get("/agent2/findings").json()["products"]
        assert products
        for p in products:
            # the console renders these unconditionally, so they must always be present
            assert "delist" in p and isinstance(p["delist"], bool)
            assert "already_removed" in p
            assert "ratings_total" in p
            assert "seller_name" in p

    def test_dead_stock_is_discoverable_without_running_an_audit(self, client):
        """The panel populates on page load — a judge shouldn't have to run the sweep first
        to see that the catalogue contains dead listings."""
        products = client.get("/agent2/findings").json()["products"]
        assert [p for p in products if p["delist"]], "no delist candidates in the seed"

"""API smoke tests — endpoint-level validation of the primary user flows.

Scope is deliberately shallow: these assert that each route wires up, enforces its
governance rules, and returns the shape the frontend consumes. The DECISION logic
underneath is covered exhaustively by the service unit tests (test_risk_checks,
test_delisting, test_tripwires, ...).

Every LLM entry point is stubbed by the `client` fixture, so the whole file runs
offline and costs no Gemini quota.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# infrastructure
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# catalog / buyer browsing
# ---------------------------------------------------------------------------
def test_products_list_and_detail(client):
    r = client.get("/products")
    assert r.status_code == 200
    products = r.json()
    assert len(products) > 0

    pid = products[0]["id"]
    detail = client.get(f"/products/{pid}")
    assert detail.status_code == 200
    body = detail.json()
    # the fields ProductView renders
    for field in ("id", "title", "price", "status", "reviews", "variants"):
        assert field in body


def test_unknown_product_is_404(client):
    assert client.get("/products/prod_does_not_exist").status_code == 404


# ---------------------------------------------------------------------------
# seller — new-listing submission gate
# ---------------------------------------------------------------------------
def test_listing_check_blocks_incomplete_submission(client):
    """An apparel listing with no description/colour/size chart must be refused,
    and the seller must be told exactly which fields are missing."""
    r = client.post("/listing/check", json={"category": "apparel", "title": "Kurti"})
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["missing"]
    assert set(body["missing"]).issubset(set(body["required"]))


def test_listing_check_allows_complete_submission(client):
    r = client.post("/listing/check", json={
        "category": "apparel",
        "title": "Rayon Embroidered Anarkali Kurti",
        "description": "A comfortable rayon kurti with thread embroidery at the yoke, "
                       "cut for everyday wear and finished with dense even seams.",
        "color": "Navy Blue",
        "fabric_claim": "100% rayon",
        "size_chart_json": {"S": "36", "M": "38", "L": "40"},
        "listing_video_path": "kurti_listing_black.mp4",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is True, f"unexpectedly blocked on: {body['missing']}"
    assert body["missing"] == []


# ---------------------------------------------------------------------------
# manager — moderation queue and decisions
# ---------------------------------------------------------------------------
def test_managers_and_queue(client):
    managers = client.get("/managers").json()
    assert len(managers) > 0
    assert {"id", "name", "seller_count"} <= set(managers[0])

    mid = managers[0]["id"]
    q = client.get(f"/manager/{mid}/queue")
    assert q.status_code == 200
    body = q.json()
    assert body["manager_id"] == mid
    assert body["queue_size"] == len(body["items"])


def test_manager_cannot_decide_on_another_managers_product(client):
    """Governance: a manager may only act on their own sellers' listings."""
    managers = client.get("/managers").json()
    owner = next(m for m in managers if client.get(f"/manager/{m['id']}/queue").json()["items"])
    item = client.get(f"/manager/{owner['id']}/queue").json()["items"][0]
    other = next(m for m in managers if m["id"] != owner["id"])

    r = client.post(f"/manager/{other['id']}/products/{item['product_id']}/decision",
                    json={"decision": "approve"})
    assert r.status_code == 403


def test_manager_decision_applies_and_clears_the_queue(client):
    """The core moderation loop: a listing case is decided, the status changes, the
    seller is notified, and the case leaves the 'action needed' queue."""
    managers = client.get("/managers").json()
    mid, item = next(
        (m["id"], items[0])
        for m in managers
        if (items := [i for i in client.get(f"/manager/{m['id']}/queue").json()["items"]
                      if i.get("kind") == "listing"])
    )
    pid = item["product_id"]

    r = client.post(f"/manager/{mid}/products/{pid}/decision",
                    json={"decision": "approve", "comment": "Checked out on review."})
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == pid
    assert body["new_status"] == "active"

    # the seller is always told what happened
    notes = client.get("/notifications", params={"audience": "seller"}).json()
    assert any(n["related_id"] == pid for n in notes)

    # and the case no longer awaits a decision
    still_queued = [i for i in client.get(f"/manager/{mid}/queue").json()["items"]
                    if i["product_id"] == pid and i.get("kind") == "listing"]
    assert still_queued == []


def test_unknown_manager_is_404(client):
    assert client.get("/manager/mgr_nope/queue").status_code == 404


# ---------------------------------------------------------------------------
# buyer dispute -> manager resolution
# ---------------------------------------------------------------------------
def test_buyer_can_open_a_dispute(client):
    """Filing a dispute records the claim and queues an investigation. The agent loop
    itself is stubbed — this asserts the intake, not the verdict."""
    buyers = client.get("/buyers").json()
    orders = client.get(f"/buyers/{buyers[0]['id']}/orders").json()["orders"]
    order = next(o for o in orders if o["dispute_available"])

    r = client.post("/dispute", json={"order_id": order["id"],
                                      "claim_type": "item_not_as_described"})
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"] == order["id"]
    assert body["status"] == "queued"

    inv = client.get(f"/investigations/{body['investigation_id']}")
    assert inv.status_code == 200
    assert inv.json()["trigger"] == "post_delivery"


def test_dispute_on_unknown_order_is_404(client):
    r = client.post("/dispute", json={"order_id": "order_nope", "claim_type": "damaged"})
    assert r.status_code == 404


def test_manager_resolves_a_dispute(client):
    """A dispute routed to manual review is ruled on by the owning manager, and the
    buyer is notified either way."""
    managers = client.get("/managers").json()
    found = None
    for m in managers:
        for item in client.get(f"/manager/{m['id']}/queue").json()["items"]:
            if item.get("kind") == "dispute":
                found = (m["id"], item)
                break
        if found:
            break
    if found is None:
        pytest.skip("no dispute currently routed to manual review in the seed")

    mid, item = found
    r = client.post(f"/manager/{mid}/disputes/{item['order_id']}/decision",
                    json={"decision": "approve", "comment": "Corroborated."})
    assert r.status_code == 200
    assert r.json()["new_status"] == "refunded"

    buyer_notes = client.get("/notifications", params={"audience": "buyer"}).json()
    assert any(n["related_id"] == item["order_id"] for n in buyer_notes)


# ---------------------------------------------------------------------------
# notifications
# ---------------------------------------------------------------------------
def test_notifications_filter_by_audience(client):
    all_notes = client.get("/notifications").json()
    seller_notes = client.get("/notifications", params={"audience": "seller"}).json()
    assert len(all_notes) >= len(seller_notes)
    assert all(n["audience"] == "seller" for n in seller_notes)


# ---------------------------------------------------------------------------
# agent surfaces
# ---------------------------------------------------------------------------
def test_agent1_evidence_is_deterministic_and_llm_free(client):
    """The always-watching layer: real risk signals with no LLM call, so the evidence
    renders even with zero Gemini quota."""
    pid = client.get("/products").json()[0]["id"]
    r = client.get("/agent1/evidence", params={"product_id": pid})
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == pid
    assert isinstance(body["risk_flags"], int)
    tools = {t["tool"] for t in body["tools"]}
    assert "check_catalog_risk" in tools
    # the retired image-authenticity stub must not reappear as advertised evidence
    labels = {s["label"] for t in body["tools"] for s in t["signals"]}
    assert "Image authenticity" not in labels


def test_agent1_evidence_requires_an_identifier(client):
    assert client.get("/agent1/evidence").status_code == 400


def test_agent2_findings_and_audit(client):
    """Agent 2's catalog audit runs deterministically (clustering stubbed) and reports
    a per-product summary the manager console consumes."""
    findings = client.get("/agent2/findings")
    assert findings.status_code == 200
    assert "products" in findings.json()

    r = client.post("/audit", json={"cluster": False})
    assert r.status_code == 200
    body = r.json()
    assert body["evaluated"] == len(body["items"])
    assert set(body["summary"]) >= {"suspended", "correction_window", "kept"}

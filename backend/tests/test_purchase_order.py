"""Kontraktstest för /api/purchase-order. Se docs/plan.md #3 för den riktiga materialbalans-
kontrollen, som gäller när app.services.cutting_optimizer är klar (FFD, docs/adr.md ADR-2).
"""

import pytest


def test_get_purchase_order_returns_200_and_matches_contract(client):
    response = client.get("/api/purchase-order")
    assert response.status_code == 200
    body = response.json()

    assert body["kerf_mm"] > 0
    assert len(body["groups"]) > 0
    assert len(body["order_lines"]) > 0


def test_bars_balance_material(client):
    """sum(cuts) + kerf_total == used_length <= purchase_length, per stång."""
    body = client.get("/api/purchase-order").json()

    for group in body["groups"]:
        for bar in group["bars"]:
            cuts_sum = sum(cut["length_mm"] for cut in bar["cuts"])
            assert cuts_sum + bar["kerf_total_mm"] == pytest.approx(bar["used_length_mm"])
            assert bar["used_length_mm"] <= bar["purchase_length_mm"]


def test_cut_oid_traceable_to_bom(client):
    """oid i en kapbit ska gå att slå upp mot /api/bom -- det är vad inkrement 4 bygger på."""
    bom_oids = {item["oid"] for item in client.get("/api/bom").json()["items"]}
    order = client.get("/api/purchase-order").json()

    for group in order["groups"]:
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                assert cut["oid"] in bom_oids

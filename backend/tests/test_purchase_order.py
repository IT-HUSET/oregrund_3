"""Kontraktstest för /api/purchase-order mot riktig FFD-kapoptimering (inkrement 3,
docs/plan.md #3, docs/adr.md ADR-2).
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


def test_spliced_segments_sum_to_piece_length(client):
    """docs/plan.md #3: för skarvade oid, sum(cuts med detta oid.length_mm) == splices.total_length_mm."""
    order = client.get("/api/purchase-order").json()

    for group in order["groups"]:
        cuts_by_oid: dict[str, list[float]] = {}
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                cuts_by_oid.setdefault(cut["oid"], []).append(cut["length_mm"])

        for splice in group["splices"]:
            segment_lengths = cuts_by_oid[splice["oid"]]
            assert len(segment_lengths) == splice["segment_count"]
            assert sum(segment_lengths) == pytest.approx(splice["total_length_mm"])
            assert splice["joint_count"] == splice["segment_count"] - 1
            assert len(splice["purchase_lengths_mm"]) == splice["segment_count"]


def test_splice_count_matches_bom_pieces_over_longest_trade_length(client):
    """Behov > längsta handelslängden (5400 mm, docs/prd.md §0) ska skarvas, inga andra."""
    bom_items = client.get("/api/bom").json()["items"]
    order = client.get("/api/purchase-order").json()

    longest_trade_length_mm = max(
        bar["purchase_length_mm"] for group in order["groups"] for bar in group["bars"]
    )
    expected_spliced = sum(1 for item in bom_items if item["length_mm"] > longest_trade_length_mm)

    assert order["summary"]["spliced_piece_count"] == expected_spliced
    assert order["summary"]["spliced_piece_count"] > 0

    total_joints = sum(s["joint_count"] for g in order["groups"] for s in g["splices"])
    assert order["summary"]["total_joints"] == total_joints

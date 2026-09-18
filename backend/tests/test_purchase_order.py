"""Kontraktstest + facit för /api/purchase-order (inkrement 3, docs/plan.md #3).

Materialbalanskontrollen från planen gäller nu den riktiga FFD-körningen (docs/adr.md ADR-2)
mot data/components.xml, inte längre en fixture.
"""

import pytest

from app.config import KERF_MM


def test_get_purchase_order_returns_200_and_matches_contract(client):
    response = client.get("/api/purchase-order")
    assert response.status_code == 200
    body = response.json()

    assert body["kerf_mm"] == KERF_MM
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
            assert bar["used_length_mm"] + bar["waste_mm"] == pytest.approx(
                bar["purchase_length_mm"]
            )


def test_cut_oid_traceable_to_bom(client):
    """oid i en kapbit ska gå att slå upp mot /api/bom -- det är vad inkrement 4 bygger på."""
    bom_oids = {item["oid"] for item in client.get("/api/bom").json()["items"]}
    order = client.get("/api/purchase-order").json()

    for group in order["groups"]:
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                assert cut["oid"] in bom_oids


def test_kerf_matches_number_of_cuts(client):
    """Konventionen är ett kerf-avdrag per kapad bit."""
    for group in client.get("/api/purchase-order").json()["groups"]:
        for bar in group["bars"]:
            assert bar["kerf_total_mm"] == pytest.approx(len(bar["cuts"]) * KERF_MM)


def test_purchase_lengths_are_real_trade_lengths(client):
    """Inga påhittade längder: allt som köps finns i CSV:n (AGENTS.md)."""
    from app.config import TRADE_LENGTHS_CSV_PATH
    from app.services.article_matching import load_trade_lengths_mm

    valid = set(load_trade_lengths_mm(TRADE_LENGTHS_CSV_PATH))
    body = client.get("/api/purchase-order").json()

    for group in body["groups"]:
        for bar in group["bars"]:
            assert bar["purchase_length_mm"] in valid
    for line in body["order_lines"]:
        assert line["purchase_length_mm"] in valid


def test_every_optimizable_piece_is_cut_exactly_once(client):
    """Varje kapbar bit ur BOM:en ska finnas i kaplistan, en gång (skarvade: en gång per segment)."""
    from app.services.article_matching import is_optimizable
    from app.services.project_data import get_frame_pieces

    expected = {p.oid: p.length_mm for p in get_frame_pieces() if is_optimizable(p)}
    order = client.get("/api/purchase-order").json()

    covered: dict[str, float] = {}
    for group in order["groups"]:
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                covered[cut["oid"]] = covered.get(cut["oid"], 0.0) + cut["length_mm"]

    assert set(covered) == set(expected)
    for oid, length in expected.items():
        assert covered[oid] == pytest.approx(length)


def test_excluded_materials_are_not_optimized(client):
    """Limträ (GL) och SHIMS kapoptimeras inte (data/dataspec.md §5) men finns kvar i BOM:en."""
    bom = client.get("/api/bom").json()["items"]
    excluded = {i["oid"] for i in bom if i["mat_code"] == "GL" or i["use"] == "SHIMS"}
    assert len(excluded) == 7

    order = client.get("/api/purchase-order").json()
    cut_oids = {
        cut["oid"] for g in order["groups"] for b in g["bars"] for cut in b["cuts"]
    }
    assert not (excluded & cut_oids)


# --- Skarvning genom hela kedjan (docs/prd.md §3.3/§7) ----------------------------------


def test_all_50_oversized_pieces_are_spliced(client):
    """50 bitar > 5400 mm (docs/prd.md §0) måste skarvas, ingen får tappas."""
    body = client.get("/api/purchase-order").json()
    assert body["summary"]["spliced_piece_count"] == 50
    assert body["summary"]["total_joints"] >= 50


def test_spliced_segments_cover_the_full_needed_length(client):
    """docs/api-contract.md: sum(cuts med detta oid) == splices[].total_length_mm."""
    bom = {i["oid"]: i["length_mm"] for i in client.get("/api/bom").json()["items"]}

    for group in client.get("/api/purchase-order").json()["groups"]:
        for splice in group["splices"]:
            covered = sum(
                cut["length_mm"]
                for bar in group["bars"]
                for cut in bar["cuts"]
                if cut["oid"] == splice["oid"]
            )
            assert covered == pytest.approx(splice["total_length_mm"])
            assert splice["total_length_mm"] == bom[splice["oid"]]
            assert splice["joint_count"] == splice["segment_count"] - 1


def test_spliced_cuts_are_flagged_in_the_data_not_just_the_ui(client):
    """docs/prd.md §7: en skarvad rad får aldrig kunna läsas som en odelad längd."""
    for group in client.get("/api/purchase-order").json()["groups"]:
        spliced_oids = {s["oid"] for s in group["splices"]}
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                if cut["oid"] in spliced_oids:
                    assert cut["spliced"] is True
                    assert 1 <= cut["segment_index"] <= cut["segment_count"]
                else:
                    assert cut["spliced"] is False


def test_no_cut_exceeds_the_longest_trade_length(client):
    """Efter skarvning ska ingen enskild kapbit vara längre än den stång den skärs ur."""
    for group in client.get("/api/purchase-order").json()["groups"]:
        for bar in group["bars"]:
            for cut in bar["cuts"]:
                assert cut["length_mm"] <= bar["purchase_length_mm"]


# --- Inköpsunderlag och spillrapport -----------------------------------------------------


def test_order_lines_aggregate_all_bars(client):
    body = client.get("/api/purchase-order").json()

    counted: dict[tuple, int] = {}
    for group in body["groups"]:
        for bar in group["bars"]:
            key = (group["code"], group["mat_code"], bar["purchase_length_mm"])
            counted[key] = counted.get(key, 0) + 1

    for line in body["order_lines"]:
        key = (line["code"], line["mat_code"], line["purchase_length_mm"])
        assert line["quantity"] == counted[key]
        assert line["total_price_sek"] == pytest.approx(
            round(line["price_per_unit_sek"] * line["quantity"], 2)
        )

    assert sum(line["quantity"] for line in body["order_lines"]) == body["summary"]["total_bars"]


def test_summary_matches_the_groups(client):
    body = client.get("/api/purchase-order").json()
    summary = body["summary"]

    purchased = sum(b["purchase_length_mm"] for g in body["groups"] for b in g["bars"])
    needed = sum(c["length_mm"] for g in body["groups"] for b in g["bars"] for c in b["cuts"])

    assert summary["total_purchased_length_mm"] == pytest.approx(purchased, abs=0.1)
    assert summary["total_needed_length_mm"] == pytest.approx(needed, abs=0.1)
    assert summary["total_cost_sek"] == pytest.approx(
        round(sum(line["total_price_sek"] for line in body["order_lines"]), 2)
    )


def test_waste_percent_is_plausible(client):
    """Spillet ska vara verkligt räknat och rimligt -- inte 0 (hårdkodat) eller absurt högt."""
    summary = client.get("/api/purchase-order").json()["summary"]
    assert 0 < summary["total_waste_percent"] < 25


def test_optimization_beats_the_unoptimized_baseline(client):
    """data/dataspec.md §7: spillrapporten jämförs mot 'en handelslängd per bit'."""
    summary = client.get("/api/purchase-order").json()["summary"]
    baseline = summary["baseline"]

    assert baseline["total_bars"] > summary["total_bars"]
    assert baseline["total_waste_percent"] > summary["total_waste_percent"]
    assert baseline["saved_length_mm"] > 0
    assert baseline["saved_cost_sek"] > 0


def test_splice_purchase_lengths_match_the_actual_bars(client):
    """`purchase_lengths_mm` ska vara de stänger segmenten FAKTISKT ligger i, inte en plan.

    FFD och krympsteget flyttar ofta ett segment till en annan handelslängd än den som
    uppskattades innan packningen — rapporteras planen säger underlaget fel längd till inköp.
    """
    for group in client.get("/api/purchase-order").json()["groups"]:
        for splice in group["splices"]:
            actual = sorted(
                (
                    bar["purchase_length_mm"]
                    for bar in group["bars"]
                    for cut in bar["cuts"]
                    if cut["oid"] == splice["oid"]
                ),
                reverse=True,
            )
            assert sorted(splice["purchase_lengths_mm"], reverse=True) == actual, splice["oid"]


def test_splice_purchase_lengths_cover_the_needed_length(client):
    """De rapporterade stängerna måste rymma behovet — annars går biten inte att bygga."""
    for group in client.get("/api/purchase-order").json()["groups"]:
        for splice in group["splices"]:
            assert len(splice["purchase_lengths_mm"]) == splice["segment_count"]
            assert sum(splice["purchase_lengths_mm"]) >= splice["total_length_mm"]

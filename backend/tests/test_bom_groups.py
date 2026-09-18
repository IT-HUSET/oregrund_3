"""Kontraktstest + facit för /api/bom/groups (inkrement 2, docs/plan.md #2).

Kontrollen från planen: gruppen 45x182/C24 innehåller exakt 72 rader och listar
handelslängderna 1800-5400 mm.
"""

from app.config import TRADE_LENGTHS_CSV_PATH
from app.services.article_matching import load_trade_lengths_mm


def _group(client, code: str, mat_code: str) -> dict:
    groups = client.get("/api/bom/groups").json()["groups"]
    return next(g for g in groups if g["code"] == code and g["mat_code"] == mat_code)


def test_get_bom_groups_returns_200_and_matches_contract(client):
    response = client.get("/api/bom/groups")
    assert response.status_code == 200

    groups = response.json()["groups"]
    assert len(groups) > 0

    group = groups[0]
    assert group["piece_count"] == len(group["pieces"])
    assert group["available_trade_lengths_mm"] == sorted(group["available_trade_lengths_mm"])


def test_45x182_c24_group_has_72_pieces(client):
    """docs/plan.md #2, facit."""
    group = _group(client, "45x182", "C24")
    assert group["piece_count"] == 72
    assert len(group["pieces"]) == 72


def test_group_lists_real_trade_lengths_from_csv(client):
    """Handelslängderna ska komma ur CSV:n, aldrig vara hårdkodade (AGENTS.md)."""
    group = _group(client, "45x182", "C24")
    lengths = group["available_trade_lengths_mm"]

    assert lengths == load_trade_lengths_mm(TRADE_LENGTHS_CSV_PATH)
    assert lengths[0] == 1800
    assert lengths[-1] == 5400
    assert all(b - a == 300 for a, b in zip(lengths, lengths[1:]))


def test_every_bom_piece_lands_in_exactly_one_group(client):
    """Ingen kapbit får tappas bort eller dubbleras i grupperingen."""
    bom_oids = [item["oid"] for item in client.get("/api/bom").json()["items"]]
    grouped_oids = [
        piece["oid"]
        for group in client.get("/api/bom/groups").json()["groups"]
        for piece in group["pieces"]
    ]

    assert sorted(grouped_oids) == sorted(bom_oids)


def test_group_total_length_matches_its_pieces(client):
    for group in client.get("/api/bom/groups").json()["groups"]:
        expected = round(sum(p["length_mm"] for p in group["pieces"]), 1)
        assert group["total_length_mm"] == expected


def test_trade_lengths_csv_is_read_not_hardcoded():
    lengths = load_trade_lengths_mm(TRADE_LENGTHS_CSV_PATH)
    assert lengths == list(range(1800, 5401, 300))

"""Kontraktstest för /api/bom/groups mot riktig data (inkrement 2, docs/plan.md #2)."""


def test_get_bom_groups_returns_200_and_matches_contract(client):
    response = client.get("/api/bom/groups")
    assert response.status_code == 200

    groups = response.json()["groups"]
    assert len(groups) > 0

    group = groups[0]
    assert group["piece_count"] == len(group["pieces"])
    assert group["available_trade_lengths_mm"] == sorted(group["available_trade_lengths_mm"])


def test_45x182_c24_group_has_72_pieces_and_trade_lengths(client):
    groups = client.get("/api/bom/groups").json()["groups"]
    group = next(g for g in groups if g["code"] == "45x182" and g["mat_code"] == "C24")

    assert group["piece_count"] == 72
    assert group["available_trade_lengths_mm"] == [
        1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400,
    ]


def test_bom_groups_cover_all_bom_pieces_exactly_once(client):
    bom_count = client.get("/api/bom").json()["count"]
    groups = client.get("/api/bom/groups").json()["groups"]

    assert sum(g["piece_count"] for g in groups) == bom_count

    all_oids = [oid for g in groups for oid in (p["oid"] for p in g["pieces"])]
    assert len(all_oids) == len(set(all_oids))

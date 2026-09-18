"""Kontraktstest för /api/bom/groups. Se docs/plan.md #2 för den riktiga kontrollen
(gruppen 45x182/C24 -> piece_count == 72), som gäller när app.services.article_matching är klar.
"""


def test_get_bom_groups_returns_200_and_matches_contract(client):
    response = client.get("/api/bom/groups")
    assert response.status_code == 200

    groups = response.json()["groups"]
    assert len(groups) > 0

    group = groups[0]
    assert group["piece_count"] == len(group["pieces"])
    assert group["available_trade_lengths_mm"] == sorted(group["available_trade_lengths_mm"])

"""Kontraktstest + facit för /api/bom (inkrement 1, docs/plan.md #1).

Kontrollen från planen: GET /api/bom -> 200, len(items) == 731, och 72 träffar för 45x182.
"""


def test_get_bom_returns_200_and_matches_contract(client):
    response = client.get("/api/bom")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == len(body["items"])

    item = body["items"][0]
    for field in (
        "oid", "item_id", "code", "width_mm", "height_mm", "length_mm",
        "mat_code", "module_name", "module_flat", "use", "bom_phase",
    ):
        assert field in item


def test_bom_contains_all_731_frame_pieces(client):
    """docs/plan.md #1, facit."""
    assert client.get("/api/bom").json()["count"] == 731


def test_filter_on_45x182_gives_72_hits(client):
    """docs/plan.md #1, klick-kontrollen -- samma filtrering som UI:t gör."""
    items = client.get("/api/bom").json()["items"]
    assert sum(1 for i in items if i["code"] == "45x182") == 72


def test_bom_items_have_unique_oid(client):
    body = client.get("/api/bom").json()
    oids = [item["oid"] for item in body["items"]]
    assert len(oids) == len(set(oids))


def test_known_oid_is_present_for_3d_traceability(client):
    """OID 589830 == IFCBEAM.Tag i 772_H811_new.ifc (docs/plan.md #4)."""
    items = {i["oid"]: i for i in client.get("/api/bom").json()["items"]}

    assert "589830" in items
    assert items["589830"]["item_id"] == "FD5"
    assert items["589830"]["code"] == "45x182"


def test_health_endpoint(client):
    assert client.get("/api/health").json() == {"status": "ok"}

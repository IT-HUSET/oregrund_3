"""Kontraktstest för /api/bom mot den riktiga components.xml (inkrement 1, docs/plan.md #1)."""


def test_get_bom_returns_200_and_matches_contract(client):
    response = client.get("/api/bom")
    assert response.status_code == 200

    body = response.json()
    assert body["count"] == len(body["items"])
    assert body["count"] > 0

    item = body["items"][0]
    for field in (
        "oid", "code", "width_mm", "height_mm", "length_mm",
        "mat_code", "use",
    ):
        assert field in item


def test_bom_has_731_items(client):
    body = client.get("/api/bom").json()
    assert body["count"] == 731
    assert len(body["items"]) == 731


def test_bom_filter_45x182_has_72_items(client):
    body = client.get("/api/bom").json()
    matches = [item for item in body["items"] if item["code"] == "45x182"]
    assert len(matches) == 72


def test_bom_items_have_unique_oid(client):
    body = client.get("/api/bom").json()
    oids = [item["oid"] for item in body["items"]]
    assert len(oids) == len(set(oids))


def test_known_piece_matches_prd_example(client):
    """OID 589830, se docs/prd.md §0 -- samma bit som IFCBEAM.Tag=589830 i .ifc-filen."""
    body = client.get("/api/bom").json()
    piece = next(item for item in body["items"] if item["oid"] == "589830")

    assert piece["item_id"] == "FD5"
    assert piece["code"] == "45x182"
    assert piece["width_mm"] == 45
    assert piece["height_mm"] == 182
    assert piece["length_mm"] == 255.0
    assert piece["mat_code"] == "C24"
    assert piece["use"] == "ÖPPNINGSREGEL"

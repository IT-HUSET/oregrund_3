"""Kontraktstest för /api/bom mot boilerplate-fixturen.

Kontrollen från docs/plan.md #1 (len(items) == 731, 72 träffar för 45x182) gäller det RIKTIGA
svaret och läggs till/uppdateras här när app.services.xml_parser är implementerad (inkrement 1).
Fram tills dess verifierar detta test bara att kontraktet (docs/api-contract.md) hålls.
"""


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


def test_bom_items_have_unique_oid(client):
    body = client.get("/api/bom").json()
    oids = [item["oid"] for item in body["items"]]
    assert len(oids) == len(set(oids))

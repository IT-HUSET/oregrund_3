"""Tester för CSV-exporten (docs/prd.md §3.5, docs/plan.md #3: 'jämför CSV:n mot UI')."""

import csv
import io


def _rows(text: str) -> list[list[str]]:
    """Läser CSV:n som Excel gör: BOM:en i början är inte data."""
    return list(csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";"))


def test_purchase_order_csv_downloads_as_csv(client):
    response = client.get("/api/purchase-order.csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "inkopsunderlag.csv" in response.headers["content-disposition"]


def test_purchase_order_csv_matches_the_json(client):
    """Exporten formaterar om samma siffror -- den får inte räkna om dem."""
    order = client.get("/api/purchase-order").json()
    rows = _rows(client.get("/api/purchase-order.csv").text)

    header, *rest = rows
    assert header[0] == "Tvärsnitt"

    data_rows = [r for r in rest if r and r[0] and r[0] != "Summering" and len(r) > 4]
    assert len(data_rows) == len(order["order_lines"])

    for row, line in zip(data_rows, order["order_lines"]):
        assert row[0] == line["code"]
        assert row[1] == line["mat_code"]
        assert int(row[2]) == line["purchase_length_mm"]
        assert int(row[3]) == line["quantity"]
        assert row[4] == line["article_number"]


def test_purchase_order_csv_contains_the_waste_report(client):
    text = client.get("/api/purchase-order.csv").text
    summary = client.get("/api/purchase-order").json()["summary"]

    assert "Spill (%)" in text
    assert f"{summary['total_waste_percent']:.2f}".replace(".", ",") in text
    assert "Skarvade bitar" in text


def test_cut_list_csv_has_one_row_per_cut(client):
    order = client.get("/api/purchase-order").json()
    expected = sum(len(bar["cuts"]) for group in order["groups"] for bar in group["bars"])

    rows = _rows(client.get("/api/cut-list.csv").text)
    assert len(rows) - 1 == expected


def test_cut_list_csv_marks_spliced_segments(client):
    """En skarvad rad måste synas som skarv i exporten (docs/prd.md §7)."""
    rows = _rows(client.get("/api/cut-list.csv").text)
    header, *data = rows
    splice_column = header.index("Skarv")

    marks = [row[splice_column] for row in data if row[splice_column]]
    assert marks, "inga skarvade rader märkta i kaplistan"
    assert all(" av " in mark for mark in marks)


def test_cut_list_csv_carries_traceability_fields(client):
    """Kapoperatören ska se OID, position (ITEM_ID), modul och rum per bit."""
    rows = _rows(client.get("/api/cut-list.csv").text)
    header = rows[0]

    for column in ("OID", "Position (ITEM_ID)", "Modul", "Rum", "Funktion", "Kaplängd (mm)"):
        assert column in column and column in header

    bom = {i["oid"]: i for i in client.get("/api/bom").json()["items"]}
    oid_col = header.index("OID")
    item_col = header.index("Position (ITEM_ID)")
    for row in rows[1:]:
        assert row[oid_col] in bom
        assert row[item_col] == (bom[row[oid_col]]["item_id"] or "")


def test_csv_starts_with_bom_for_swedish_excel(client):
    """Utan BOM avkodar Excel filen med ANSI och åäö blir mojibake i rubrikerna."""
    for path in ("/api/purchase-order.csv", "/api/cut-list.csv"):
        text = client.get(path).text
        assert text.startswith("\ufeff"), path
        assert "Tvärsnitt" in text


def test_cut_list_bar_ids_are_numbered_per_group(client):
    """Kaplistans stång-id måste matcha UI:t, som numrerar om från #001 i varje grupp."""
    rows = _rows(client.get("/api/cut-list.csv").text)
    header, *data = rows
    bar_col, code_col, mat_col = header.index("Stång"), header.index("Tvärsnitt"), header.index("Klass")

    first_id_per_group: dict[tuple[str, str], str] = {}
    for row in data:
        key = (row[code_col], row[mat_col])
        first_id_per_group.setdefault(key, row[bar_col])

    for (code, mat_code), bar_id in first_id_per_group.items():
        assert bar_id == f"{mat_code}-{code}-#001", f"{code}/{mat_code} började på {bar_id}"


def test_cut_list_bar_ids_match_the_ui_labels(client):
    """Samma etikett som PurchaseOrderView bygger: {klass}-{tvärsnitt}-#{index+1}."""
    order = client.get("/api/purchase-order").json()
    expected = [
        f"{g['mat_code']}-{g['code']}-#{i + 1:03d}"
        for g in order["groups"]
        for i, bar in enumerate(g["bars"])
        for _ in bar["cuts"]
    ]

    rows = _rows(client.get("/api/cut-list.csv").text)
    bar_col = rows[0].index("Stång")
    assert [row[bar_col] for row in rows[1:]] == expected

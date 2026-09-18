"""CSV-export av inköpsunderlag och kaplista (docs/prd.md §3.5).

Formaterar om siffrorna från PurchaseOrderResponse — räknar aldrig om dem, så exporten och
UI:t kan inte glida isär (docs/plan.md #3: 'öppna CSV:n, jämför mot UI').

Separatorn är semikolon och decimaltecknet komma: filen ska öppnas i svensk Excel av en
inköpare, inte parsas av ett annat program.
"""

import csv
import io

from app.models import FramePieceOut, PurchaseOrderResponse


#: Excel på Windows avkodar en .csv med ANSI-kodsidan om filen saknar BOM — då blir
#: "Tvärsnitt" till "TvÃ¤rsnitt". Semikolon och decimalkomma ovan siktar redan på svensk
#: Excel, så filen inleds med BOM för att åäö ska överleva.
BOM = "\ufeff"


def _number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def _writer() -> tuple[io.StringIO, "csv._writer"]:
    buffer = io.StringIO()
    buffer.write(BOM)
    return buffer, csv.writer(buffer, delimiter=";", lineterminator="\r\n")


def purchase_order_csv(order: PurchaseOrderResponse) -> str:
    """En rad per inköpsartikel, plus en summeringssektion med spillrapporten."""
    buffer, writer = _writer()

    writer.writerow(
        [
            "Tvärsnitt", "Klass", "Handelslängd (mm)", "Antal",
            "Artikelnummer", "Pris/st (SEK)", "Summa (SEK)", "Leveranstid (dagar)",
        ]
    )
    for line in order.order_lines:
        writer.writerow(
            [
                line.code, line.mat_code, line.purchase_length_mm, line.quantity,
                line.article_number, _number(line.price_per_unit_sek, 2),
                _number(line.total_price_sek, 2), line.lead_time_days,
            ]
        )

    summary = order.summary
    writer.writerow([])
    writer.writerow(["Summering"])
    writer.writerow(["Antal stänger", summary.total_bars])
    writer.writerow(["Behövd längd (m)", _number(summary.total_needed_length_mm / 1000)])
    writer.writerow(["Inköpt längd (m)", _number(summary.total_purchased_length_mm / 1000)])
    writer.writerow(["Spill (%)", _number(summary.total_waste_percent, 2)])
    writer.writerow(["Total kostnad (SEK)", _number(summary.total_cost_sek, 2)])
    writer.writerow(["Skarvade bitar", summary.spliced_piece_count])
    writer.writerow(["Antal skarvar", summary.total_joints])
    writer.writerow(["Kerf (mm)", _number(order.kerf_mm)])
    writer.writerow([])
    writer.writerow(["Pris, artikelnummer och leveranstid är mockade, se docs/prd.md §4."])

    return buffer.getvalue()


def cut_list_csv(
    order: PurchaseOrderResponse, pieces_by_oid: dict[str, FramePieceOut]
) -> str:
    """En rad per kapbit: vilken stång den skärs ur, i vilken ordning, och varifrån den kommer.

    `Skarv` är tom för en vanlig bit och '2 av 3' för ett segment av en skarvad bit — så att
    en skarvad rad aldrig kan läsas som en odelad längd (docs/prd.md §7).
    """
    buffer, writer = _writer()

    writer.writerow(
        [
            "Stång", "Tvärsnitt", "Klass", "Handelslängd (mm)", "Position i stång",
            "OID", "Position (ITEM_ID)", "Kaplängd (mm)", "Skarv",
            "Modul", "Rum", "Funktion",
        ]
    )

    for group in order.groups:
        # Numreringen är per grupp och 1-baserad — exakt som PurchaseOrderView visar den, så
        # att en utskriven kaplista och skärmen pekar på samma stång (docs/plan.md #3).
        for bar_number, bar in enumerate(group.bars, start=1):
            bar_id = f"{group.mat_code}-{group.code}-#{bar_number:03d}"
            for position, cut in enumerate(bar.cuts, start=1):
                piece = pieces_by_oid.get(cut.oid)
                splice = (
                    f"{cut.segment_index} av {cut.segment_count}" if cut.spliced else ""
                )
                writer.writerow(
                    [
                        bar_id, group.code, group.mat_code, bar.purchase_length_mm, position,
                        cut.oid, piece.item_id if piece else "", _number(cut.length_mm), splice,
                        (piece.module_name if piece else "") or "",
                        (piece.module_flat if piece else "") or "",
                        piece.use if piece else "",
                    ]
                )

    return buffer.getvalue()

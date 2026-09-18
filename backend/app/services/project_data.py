"""Inläst projektdata, en gång per process.

components.xml (731 FRAMEPIECE) och handelslängds-CSV:n läses vid första anropet och cachas —
de ändras aldrig under körning (AGENTS.md: filerna läses, aldrig skrivs). Routrarna i
app/routers/ går via den här modulen i stället för att parsa om per request.

Backend öppnar aldrig .ifc-filen (docs/adr.md ADR-3) — den finns inte ens som sökväg i config.
"""

from functools import lru_cache

from app.config import COMPONENTS_XML_PATH, KERF_MM, TRADE_LENGTHS_CSV_PATH
from app.models import (
    BomGroup,
    FramePieceOut,
    GroupCuttingResult,
    PurchaseOrderResponse,
)
from app.services import article_matching, cutting_optimizer
from app.services.xml_parser import parse_components_xml


@lru_cache(maxsize=1)
def get_frame_pieces() -> tuple[FramePieceOut, ...]:
    """Alla 731 FRAMEPIECE ur components.xml, i filens ordning (docs/plan.md #1)."""
    return tuple(parse_components_xml(COMPONENTS_XML_PATH))


@lru_cache(maxsize=1)
def get_trade_lengths_mm() -> tuple[int, ...]:
    """Handelslängder ur data/svensktra_standardlangder_mm.csv — aldrig hårdkodade."""
    return tuple(article_matching.load_trade_lengths_mm(TRADE_LENGTHS_CSV_PATH))


@lru_cache(maxsize=1)
def get_pieces_by_oid() -> dict[str, FramePieceOut]:
    """OID -> kapbit. Används av CSV-exporten för att berika kaplistan med modul/rum/funktion."""
    return {piece.oid: piece for piece in get_frame_pieces()}


@lru_cache(maxsize=1)
def get_bom_groups() -> tuple[BomGroup, ...]:
    """Alla grupper (code, mat_code), inklusive de som inte kapoptimeras."""
    return tuple(
        article_matching.group_by_code_and_material(
            list(get_frame_pieces()), list(get_trade_lengths_mm())
        )
    )


@lru_cache(maxsize=1)
def get_purchase_order() -> PurchaseOrderResponse:
    """Kapoptimering + inköpsunderlag + spillrapport (docs/plan.md #3).

    Bara kapbara grupper går in i optimeringen: limträ (GL) och SHIMS lyfts ur enligt
    data/dataspec.md §5. De syns fortfarande i /api/bom och /api/bom/groups.
    """
    optimizable_oids = {
        piece.oid for piece in get_frame_pieces() if article_matching.is_optimizable(piece)
    }

    results: list[GroupCuttingResult] = []
    for group in get_bom_groups():
        pieces = [piece for piece in group.pieces if piece.oid in optimizable_oids]
        if not pieces:
            continue
        # Räkna om aggregaten också — annars beskriver kopian fel antal/längd så fort en grupp
        # bara är delvis undantagen (alla är det inte i 772_H811, men regeln är per bit).
        filtered = group.model_copy(
            update={
                "pieces": pieces,
                "piece_count": len(pieces),
                "total_length_mm": round(sum(piece.length_mm for piece in pieces), 1),
            }
        )
        results.append(cutting_optimizer.optimize_group(filtered, KERF_MM))

    order_lines = cutting_optimizer.build_order_lines(results)
    summary = cutting_optimizer.build_summary(results, order_lines)
    summary.baseline = cutting_optimizer.build_baseline(results, list(get_trade_lengths_mm()))

    return PurchaseOrderResponse(
        kerf_mm=KERF_MM,
        groups=results,
        order_lines=order_lines,
        summary=summary,
    )

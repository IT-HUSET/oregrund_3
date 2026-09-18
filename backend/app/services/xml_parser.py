"""Parsa components.xml -> lista av FramePieceOut.

Inkrement 1, docs/plan.md rad 1. Backend öppnar ALDRIG .ifc-filen (docs/adr.md ADR-3) —
bara components.xml.
"""

from pathlib import Path

from app.models import FramePieceOut


def parse_components_xml(path: Path) -> list[FramePieceOut]:
    """Läs in alla <FRAMEPIECE>-element ur components.xml till FramePieceOut.

    Kontroll (docs/plan.md #1): len(resultat) == 731; filtrera code == "45x182" -> 72 träffar.

    Förslag på implementation: xml.etree.ElementTree.iterparse (filen är stor, undvik att
    bygga hela DOM:en i minnet om det går enkelt). Varje <FRAMEPIECE OID="..."> har ett
    <ATTRIBUTES>-barn med CODE, WIDTH, HEIGHT, LENGTH, MAT_CODE, MODULE_NAME, MODULE_FLAT,
    USE, ITEM_ID, BOM_PHASE — se docs/api-contract.md för fältmappning.
    """
    raise NotImplementedError("Inkrement 1, se docs/plan.md rad 1 och docs/api-contract.md")

"""Parsa components.xml -> lista av FramePieceOut.

Inkrement 1, docs/plan.md rad 1. Backend öppnar ALDRIG .ifc-filen (docs/adr.md ADR-3) —
bara components.xml.
"""

from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

from app.config import COMPONENTS_XML_PATH
from app.models import FramePieceOut


def parse_components_xml(path: Path) -> list[FramePieceOut]:
    """Läs in alla <FRAMEPIECE>-element ur components.xml till FramePieceOut.

    Ingen filtrering här (docs/plan.md #1 vill ha "alla FRAMEPIECE") — normalisering/exkludering
    (GL, SHIMS, >5400 mm m.m., se data/dataspec.md §5) hör till artikelmatchning/kapoptimering
    (inkrement 2/3), inte inläsningen.

    Kontroll (docs/plan.md #1): len(resultat) == 731; filtrera code == "45x182" -> 72 träffar.
    """
    pieces: list[FramePieceOut] = []

    for _, elem in ET.iterparse(path, events=("end",)):
        if elem.tag != "FRAMEPIECE":
            continue

        attributes = elem.find("ATTRIBUTES")
        fields = {child.tag: child.text for child in attributes}

        pieces.append(
            FramePieceOut(
                oid=elem.get("OID"),
                item_id=fields.get("ITEM_ID"),
                code=fields["CODE"],
                width_mm=float(fields["WIDTH"]),
                height_mm=round(float(fields["HEIGHT"])),
                length_mm=float(fields["LENGTH"]),
                mat_code=fields["MAT_CODE"],
                module_name=fields.get("MODULE_NAME"),
                module_flat=fields.get("MODULE_FLAT"),
                use=fields["USE"],
                bom_phase=fields.get("BOM_PHASE"),
            )
        )
        elem.clear()

    return pieces


@lru_cache(maxsize=1)
def get_frame_pieces() -> list[FramePieceOut]:
    """Cachad inläsning av components.xml -- parsas en gång per processlivstid.

    Se docs/adr.md skiss ("Läser vid start: components.xml"): main.py värmer cachen vid
    app-start, så varje request efter det är gratis.
    """
    return parse_components_xml(COMPONENTS_XML_PATH)

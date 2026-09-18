"""Parsa components.xml -> lista av FramePieceOut.

Inkrement 1, docs/plan.md rad 1. Backend öppnar ALDRIG .ifc-filen (docs/adr.md ADR-3) —
bara components.xml. Filen läses, aldrig skrivs (AGENTS.md).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from app.models import FramePieceOut

#: Fält som läses ur <ATTRIBUTES>. Se docs/api-contract.md för fältmappningen.
_REQUIRED_TEXT_FIELDS = ("CODE", "MAT_CODE", "USE")
_OPTIONAL_TEXT_FIELDS = ("ITEM_ID", "MODULE_NAME", "MODULE_FLAT", "BOM_PHASE")
_NUMERIC_FIELDS = ("WIDTH", "HEIGHT", "LENGTH")

#: START_/END_-vinklarna är 0.00 i hela detta projekt = rak kap. Är de det inte i ett annat
#: underlag håller kapoptimeringens längdmatematik inte (docs/../data/dataspec.md §5), så vi
#: räknar dem i stället för att tyst anta rakkap.
_ANGLE_FIELDS = ("START_ANGX", "START_ANGY", "END_ANGX", "END_ANGY")


class ComponentsXmlError(ValueError):
    """components.xml saknar ett fält som datamodellen kräver."""


def _text(attributes: ET.Element, name: str) -> str | None:
    node = attributes.find(name)
    if node is None or node.text is None:
        return None
    text = node.text.strip()
    return text or None


def _parse_frame_piece(element: ET.Element) -> tuple[FramePieceOut, bool]:
    """En <FRAMEPIECE> -> (FramePieceOut, har_vinklad_kap)."""
    oid = element.get("OID")
    if not oid:
        raise ComponentsXmlError("FRAMEPIECE saknar OID — utan den går 3D-spårbarheten förlorad")

    attributes = element.find("ATTRIBUTES")
    if attributes is None:
        raise ComponentsXmlError(f"FRAMEPIECE OID={oid} saknar <ATTRIBUTES>")

    values: dict[str, str] = {}
    for name in _REQUIRED_TEXT_FIELDS + _NUMERIC_FIELDS:
        text = _text(attributes, name)
        if text is None:
            raise ComponentsXmlError(f"FRAMEPIECE OID={oid} saknar {name}")
        values[name] = text

    angled = any(float(_text(attributes, name) or 0.0) != 0.0 for name in _ANGLE_FIELDS)

    return (
        FramePieceOut(
            oid=oid,
            item_id=_text(attributes, "ITEM_ID"),
            code=values["CODE"],
            width_mm=float(values["WIDTH"]),
            height_mm=float(values["HEIGHT"]),
            length_mm=float(values["LENGTH"]),
            mat_code=values["MAT_CODE"],
            module_name=_text(attributes, "MODULE_NAME"),
            module_flat=_text(attributes, "MODULE_FLAT"),
            use=values["USE"],
            bom_phase=_text(attributes, "BOM_PHASE"),
        ),
        angled,
    )


def parse_components_xml(path: Path) -> list[FramePieceOut]:
    """Läs in alla <FRAMEPIECE>-element ur components.xml till FramePieceOut.

    Kontroll (docs/plan.md #1): len(resultat) == 731; filtrera code == "45x182" -> 72 träffar.

    iterparse används för att slippa hålla hela DOM:en i minnet: varje FRAMEPIECE konverteras
    och släpps direkt. Poster med vinklad kap (START_/END_ANG != 0) räknas och loggas som en
    varning — de förekommer inte i 772_H811 men bryter längdmatematiken om de dyker upp.
    """
    pieces: list[FramePieceOut] = []
    angled_oids: list[str] = []

    for _event, element in ET.iterparse(path, events=("end",)):
        if element.tag != "FRAMEPIECE":
            continue
        piece, angled = _parse_frame_piece(element)
        pieces.append(piece)
        if angled:
            angled_oids.append(piece.oid)
        element.clear()

    if angled_oids:
        import warnings

        warnings.warn(
            f"{len(angled_oids)} FRAMEPIECE har vinklad kap (START_/END_ANG != 0), "
            f"t.ex. OID {angled_oids[:5]}. Kaplängderna behandlas ändå som rakkap "
            "(data/dataspec.md §5).",
            stacklevel=2,
        )

    return pieces

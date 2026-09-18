"""Enhetstester för inkrement 1: components.xml -> FramePieceOut (docs/plan.md #1).

Facit är uppmätt i den riktiga filen (data/dataspec.md §1): 731 FRAMEPIECE, varav 72 med
tvärsnitt 45x182.
"""

import pytest

from app.config import COMPONENTS_XML_PATH
from app.services.project_data import get_frame_pieces
from app.services.xml_parser import ComponentsXmlError, parse_components_xml


def test_parses_all_731_frame_pieces():
    assert len(get_frame_pieces()) == 731


def test_45x182_has_72_pieces():
    """docs/plan.md #1, klick-kontrollen: filtrera på 45x182 -> 72 träffar."""
    assert sum(1 for p in get_frame_pieces() if p.code == "45x182") == 72


def test_oid_is_unique_across_all_pieces():
    """OID är primärnyckeln och måste vara unik — hela 3D-spårbarheten hänger på den."""
    pieces = get_frame_pieces()
    assert len({p.oid for p in pieces}) == len(pieces)


def test_known_piece_matches_source_xml():
    """OID 589830, samma bit som nämns i docs/prd.md §0 och i IFC:n som Tag='589830'."""
    piece = next(p for p in get_frame_pieces() if p.oid == "589830")

    assert piece.item_id == "FD5"
    assert piece.code == "45x182"
    assert piece.width_mm == 45
    assert piece.height_mm == 182
    assert piece.length_mm == 255.0
    assert piece.mat_code == "C24"
    assert piece.module_name == "131"
    assert piece.module_flat == "TVÄTT"
    assert piece.use == "ÖPPNINGSREGEL"


def test_utf8_entities_are_decoded():
    """XML:en är UTF-8 med entiteter (&#196; = Ä), data/dataspec.md §4.3."""
    uses = {p.use for p in get_frame_pieces()}
    assert "ÖPPNINGSREGEL" in uses


def test_length_range_matches_dataspec():
    """47-9725 mm enligt docs/prd.md §0 — fångar om fel fält lästs som längd."""
    lengths = [p.length_mm for p in get_frame_pieces()]
    assert min(lengths) == 47.0
    assert max(lengths) == 9725.0


def test_pieces_longer_than_longest_trade_length():
    """50 bitar överstiger 5400 mm och kräver skarvning (docs/prd.md §0)."""
    assert sum(1 for p in get_frame_pieces() if p.length_mm > 5400) == 50


def test_non_integer_dimensions_are_kept():
    """3 SHIMS-bitar har tjocklek 9.76/9.78/17.55 mm — modellen måste tillåta float."""
    thin = [p for p in get_frame_pieces() if p.width_mm % 1]
    assert len(thin) == 3
    assert all(p.use == "SHIMS" for p in thin)


def test_missing_required_field_raises(tmp_path):
    """Ett underlag utan LENGTH ska larma, inte tyst ge en bit utan längd."""
    broken = tmp_path / "broken.xml"
    broken.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<COMPONENTS><FRAMEPIECE OID="1"><ATTRIBUTES>'
        "<CODE>45x95</CODE><WIDTH>45</WIDTH><HEIGHT>95</HEIGHT>"
        "<MAT_CODE>C24</MAT_CODE><USE>REGEL</USE>"
        "</ATTRIBUTES></FRAMEPIECE></COMPONENTS>",
        encoding="utf-8",
    )

    with pytest.raises(ComponentsXmlError, match="LENGTH"):
        parse_components_xml(broken)


def test_angled_cut_warns(tmp_path):
    """Vinklad kap bryter längdmatematiken — den ska varna, inte passera tyst."""
    angled = tmp_path / "angled.xml"
    angled.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<COMPONENTS><FRAMEPIECE OID="1"><ATTRIBUTES>'
        "<CODE>45x95</CODE><WIDTH>45</WIDTH><HEIGHT>95</HEIGHT><LENGTH>1000</LENGTH>"
        "<MAT_CODE>C24</MAT_CODE><USE>REGEL</USE><START_ANGX>15.0</START_ANGX>"
        "</ATTRIBUTES></FRAMEPIECE></COMPONENTS>",
        encoding="utf-8",
    )

    with pytest.warns(UserWarning, match="vinklad kap"):
        parse_components_xml(angled)


def test_source_file_is_never_written():
    """AGENTS.md: components.xml läses, aldrig skrivs."""
    before = COMPONENTS_XML_PATH.stat().st_mtime
    parse_components_xml(COMPONENTS_XML_PATH)
    assert COMPONENTS_XML_PATH.stat().st_mtime == before

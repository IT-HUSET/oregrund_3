"""GET /api/bom och GET /api/bom/groups. Se docs/api-contract.md.

Båda läser nu riktig data: /api/bom parsar components.xml (app/services/xml_parser.py,
inkrement 1), /api/bom/groups grupperar den mot handelslängder ur
data/svensktra_standardlangder_mm.csv (app/services/article_matching.py, inkrement 2).
"""

from fastapi import APIRouter

from app.models import BomGroupsResponse, BomResponse
from app.services.article_matching import get_trade_lengths_mm, group_by_code_and_material
from app.services.xml_parser import get_frame_pieces

router = APIRouter(prefix="/api", tags=["bom"])


@router.get("/bom", response_model=BomResponse)
def get_bom() -> BomResponse:
    pieces = get_frame_pieces()
    return BomResponse(count=len(pieces), items=pieces)


@router.get("/bom/groups", response_model=BomGroupsResponse)
def get_bom_groups() -> BomGroupsResponse:
    groups = group_by_code_and_material(get_frame_pieces(), get_trade_lengths_mm())
    return BomGroupsResponse(groups=groups)

"""GET /api/bom och GET /api/bom/groups. Se docs/api-contract.md.

/api/bom läser nu components.xml på riktigt (app/services/xml_parser.py, inkrement 1).
/api/bom/groups svarar fortfarande med fixture-data (app/services/fixtures.py) -- byt ut mot
app.services.article_matching när inkrement 2 (docs/plan.md) är klart; responsformen
(BomGroupsResponse) ändras inte.
"""

from fastapi import APIRouter

from app.models import BomGroupsResponse, BomResponse
from app.services import fixtures
from app.services.xml_parser import get_frame_pieces

router = APIRouter(prefix="/api", tags=["bom"])


@router.get("/bom", response_model=BomResponse)
def get_bom() -> BomResponse:
    pieces = get_frame_pieces()
    return BomResponse(count=len(pieces), items=pieces)


@router.get("/bom/groups", response_model=BomGroupsResponse)
def get_bom_groups() -> BomGroupsResponse:
    return fixtures.get_bom_groups_response()

"""GET /api/bom och GET /api/bom/groups. Se docs/api-contract.md.

Svarar just nu med fixture-data (app/services/fixtures.py). Byt ut mot
app.services.xml_parser.parse_components_xml() / app.services.article_matching när inkrement 1/2
(docs/plan.md) är klara -- responsformen (BomResponse/BomGroupsResponse) ändras inte.
"""

from fastapi import APIRouter

from app.models import BomGroupsResponse, BomResponse
from app.services import fixtures

router = APIRouter(prefix="/api", tags=["bom"])


@router.get("/bom", response_model=BomResponse)
def get_bom() -> BomResponse:
    return fixtures.get_bom_response()


@router.get("/bom/groups", response_model=BomGroupsResponse)
def get_bom_groups() -> BomGroupsResponse:
    return fixtures.get_bom_groups_response()

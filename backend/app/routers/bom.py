"""GET /api/bom och GET /api/bom/groups. Se docs/api-contract.md.

Läser riktig data ur data/components.xml via app.services.project_data (inkrement 1 och 2,
docs/plan.md). Responsformen är oförändrad mot boilerplate-läget.
"""

from fastapi import APIRouter

from app.models import BomGroupsResponse, BomResponse
from app.services import project_data

router = APIRouter(prefix="/api", tags=["bom"])


@router.get("/bom", response_model=BomResponse)
def get_bom() -> BomResponse:
    """Alla FRAMEPIECE ur components.xml (docs/plan.md #1: 731 rader)."""
    pieces = list(project_data.get_frame_pieces())
    return BomResponse(count=len(pieces), items=pieces)


@router.get("/bom/groups", response_model=BomGroupsResponse)
def get_bom_groups() -> BomGroupsResponse:
    """BOM grupperad per (tvärsnitt, klass), matchad mot handelslängder (docs/plan.md #2)."""
    return BomGroupsResponse(groups=list(project_data.get_bom_groups()))

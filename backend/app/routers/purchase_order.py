"""GET /api/purchase-order. Se docs/api-contract.md.

Kör riktig FFD-kapoptimering (app/services/cutting_optimizer.py, inkrement 3) per grupp ur
app.services.article_matching, inkl. skarvning av behov > längsta handelslängden.
"""

from fastapi import APIRouter

from app.config import KERF_MM
from app.models import PurchaseOrderResponse
from app.services.article_matching import get_trade_lengths_mm, group_by_code_and_material
from app.services.cutting_optimizer import build_order_lines, build_summary, optimize_group
from app.services.xml_parser import get_frame_pieces

router = APIRouter(prefix="/api", tags=["purchase-order"])


@router.get("/purchase-order", response_model=PurchaseOrderResponse)
def get_purchase_order() -> PurchaseOrderResponse:
    groups = group_by_code_and_material(get_frame_pieces(), get_trade_lengths_mm())
    results = [optimize_group(group, KERF_MM) for group in groups]
    order_lines = build_order_lines(results)
    summary = build_summary(results, order_lines)

    return PurchaseOrderResponse(
        kerf_mm=KERF_MM, groups=results, order_lines=order_lines, summary=summary
    )

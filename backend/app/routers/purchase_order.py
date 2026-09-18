"""GET /api/purchase-order. Se docs/api-contract.md.

Kör kapoptimering (app/services/cutting_optimizer.py, inkrement 3) per grupp ur
app.services.article_matching, inkl. skarvning av behov > längsta handelslängden. Standard är
girig FFD (docs/adr.md ADR-2); ?algorithm=exact kör OR-Tools CP-SAT istället (ADR-2-tillägget)
-- explicit användarval, inte standard, eftersom det tar sekunder-minuter snarare än
millisekunder.
"""

from typing import Literal

from fastapi import APIRouter, Query

from app.config import EXACT_SOLVER_TIME_BUDGET_S, KERF_MM
from app.models import PurchaseOrderResponse
from app.services.article_matching import get_trade_lengths_mm, group_by_code_and_material
from app.services.cutting_optimizer import build_order_lines, build_summary, optimize_group
from app.services.xml_parser import get_frame_pieces

router = APIRouter(prefix="/api", tags=["purchase-order"])


@router.get("/purchase-order", response_model=PurchaseOrderResponse)
def get_purchase_order(
    algorithm: Literal["greedy", "exact"] = Query(
        "greedy",
        description=(
            "greedy (default, millisekunder) eller exact (OR-Tools CP-SAT, sekunder-minuter, "
            "se docs/adr.md ADR-2-tillägget) -- exact ska triggas av ett explicit användarval i "
            "UI:t, inte köras vid vanlig sidladdning."
        ),
    ),
) -> PurchaseOrderResponse:
    groups = group_by_code_and_material(get_frame_pieces(), get_trade_lengths_mm())
    results = [
        optimize_group(group, KERF_MM, algorithm=algorithm, time_budget_s=EXACT_SOLVER_TIME_BUDGET_S)
        for group in groups
    ]
    order_lines = build_order_lines(results)
    summary = build_summary(results, order_lines)

    return PurchaseOrderResponse(
        kerf_mm=KERF_MM,
        algorithm=algorithm,
        groups=results,
        order_lines=order_lines,
        summary=summary,
    )

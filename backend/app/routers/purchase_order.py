"""GET /api/purchase-order. Se docs/api-contract.md.

Kör den riktiga FFD-kapoptimeringen (docs/adr.md ADR-2) via app.services.project_data,
inkrement 3 i docs/plan.md. Responsformen är oförändrad mot boilerplate-läget.
"""

from fastapi import APIRouter, Response

from app.models import PurchaseOrderResponse
from app.services import csv_export, project_data

router = APIRouter(prefix="/api", tags=["purchase-order"])


@router.get("/purchase-order", response_model=PurchaseOrderResponse)
def get_purchase_order() -> PurchaseOrderResponse:
    return project_data.get_purchase_order()


@router.get("/purchase-order.csv", response_class=Response)
def get_purchase_order_csv() -> Response:
    """Inköpsunderlaget som CSV (docs/prd.md §3.5: exporterbart underlag).

    Samma siffror som JSON-svaret ovan — exporten formaterar bara om dem, den räknar inte om.
    """
    body = csv_export.purchase_order_csv(project_data.get_purchase_order())
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inkopsunderlag.csv"'},
    )


@router.get("/cut-list.csv", response_class=Response)
def get_cut_list_csv() -> Response:
    """Kaplistan som CSV — en rad per kapbit, för kapoperatören (docs/prd.md §2).

    Skarvade bitar får en rad per segment, märkta, så de inte kan förväxlas med en odelad
    bit vid sågen (docs/prd.md §7, risken 'skarvad bit tolkas som en enda odelad längd').
    """
    body = csv_export.cut_list_csv(
        project_data.get_purchase_order(), project_data.get_pieces_by_oid()
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="kaplista.csv"'},
    )

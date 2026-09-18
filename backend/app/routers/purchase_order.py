"""GET /api/purchase-order. Se docs/api-contract.md.

Svarar just nu med fixture-data (app/services/fixtures.py). Byt ut mot
app.services.cutting_optimizer när inkrement 3 (docs/plan.md) är klart -- responsformen
(PurchaseOrderResponse) ändras inte.
"""

from fastapi import APIRouter

from app.models import PurchaseOrderResponse
from app.services import fixtures

router = APIRouter(prefix="/api", tags=["purchase-order"])


@router.get("/purchase-order", response_model=PurchaseOrderResponse)
def get_purchase_order() -> PurchaseOrderResponse:
    return fixtures.get_purchase_order_response()

"""Fixture-/mockdata för boilerplate-läget.

/api/bom och /api/bom/groups är kopplade till riktig data nu (app/services/xml_parser.py resp.
app/services/article_matching.py, inkrement 1/2) och använder inte längre något härifrån.
/api/purchase-order svarar fortfarande med fixture-data -- byt ut mot
app.services.cutting_optimizer när inkrement 3 (docs/plan.md) är klart; responsformen
(PurchaseOrderResponse) ändras inte.

OID:erna nedan är INTE hittepå: de är kopierade rakt av ur riktiga <FRAMEPIECE>-poster i
data/components.xml (589830/589831/589832, samma OID som nämns i docs/prd.md §0 och som
IFCBEAM.Tag i 772_H811_new.ifc). Kapoptimeringsexemplet för gruppen 45x182/C24 är en verklig
girig FFD-körning (kerf=3.0 mm) på just de tre bitarna, inte påhittade tal.
"""

from app.config import KERF_MM
from app.models import (
    Bar,
    Cut,
    GroupCuttingResult,
    PurchaseOrderLine,
    PurchaseOrderResponse,
    PurchaseOrderSummary,
)

# Mockat pris per löpmeter (SEK), per hållfasthetsklass. Riktiga priser är inte offentligt
# tillgängliga, se docs/prd.md §4.
MOCK_PRICE_PER_METER_SEK = {"C14": 28.0, "C16": 32.0, "C24": 38.0, "GL": 65.0, "CHS": 30.0}
MOCK_LEAD_TIME_DAYS = 5


def get_purchase_order_response() -> PurchaseOrderResponse:
    """Enda gruppen (45x182/C24) är en riktig FFD-körning på fixture-bitarna, se moduldocstring.
    Övriga grupper i fixture-BOM:en har bara en bit var och packas inte här (boilerplate-läge).
    """
    group_result = GroupCuttingResult(
        code="45x182",
        mat_code="C24",
        waste_percent=28.84,
        bars=[
            Bar(
                purchase_length_mm=3300,
                cuts=[Cut(oid="589832", length_mm=3110.0)],
                used_length_mm=3113.0,
                kerf_total_mm=KERF_MM,
                waste_mm=187.0,
            ),
            Bar(
                purchase_length_mm=1800,
                cuts=[Cut(oid="589830", length_mm=255.0), Cut(oid="589831", length_mm=255.0)],
                used_length_mm=516.0,
                kerf_total_mm=2 * KERF_MM,
                waste_mm=1284.0,
            ),
        ],
    )

    order_lines = [
        PurchaseOrderLine(
            code="45x182", mat_code="C24", purchase_length_mm=3300, quantity=1,
            article_number="MOCK-45x182-C24-3300",
            price_per_unit_sek=round(3.3 * MOCK_PRICE_PER_METER_SEK["C24"], 2),
            lead_time_days=MOCK_LEAD_TIME_DAYS,
            total_price_sek=round(3.3 * MOCK_PRICE_PER_METER_SEK["C24"], 2),
        ),
        PurchaseOrderLine(
            code="45x182", mat_code="C24", purchase_length_mm=1800, quantity=1,
            article_number="MOCK-45x182-C24-1800",
            price_per_unit_sek=round(1.8 * MOCK_PRICE_PER_METER_SEK["C24"], 2),
            lead_time_days=MOCK_LEAD_TIME_DAYS,
            total_price_sek=round(1.8 * MOCK_PRICE_PER_METER_SEK["C24"], 2),
        ),
    ]

    summary = PurchaseOrderSummary(
        total_bars=len(group_result.bars),
        total_needed_length_mm=3620.0,
        total_purchased_length_mm=5100.0,
        total_waste_percent=group_result.waste_percent,
        total_cost_sek=sum(line.total_price_sek for line in order_lines),
    )

    return PurchaseOrderResponse(
        kerf_mm=KERF_MM,
        groups=[group_result],
        order_lines=order_lines,
        summary=summary,
    )

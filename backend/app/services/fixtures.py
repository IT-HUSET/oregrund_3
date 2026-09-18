"""Fixture-/mockdata för boilerplate-läget.

Allt härifrån ersätts av app/services/{xml_parser,article_matching,cutting_optimizer}.py när
respektive inkrement (docs/plan.md) är klart — routrarna i app/routers/ importerar bara härifrån
tills dess, så svarsformen är redan den riktiga (docs/api-contract.md) fast med en handfull rader.

Raderna nedan är INTE hittepå: de är kopierade rakt av ur riktiga <FRAMEPIECE>-poster i
data/components.xml (bl.a. OID 589830/589831/589832, samma OID som nämns i docs/prd.md §0 och
som IFCBEAM.Tag i 772_H811_new.ifc). Kapoptimeringsexemplet för gruppen 45x182/C24 är en verklig
girig FFD-körning (kerf=3.0 mm) på just de tre bitarna, inte påhittade tal.
"""

from app.config import KERF_MM
from app.models import (
    Bar,
    BomGroup,
    BomGroupsResponse,
    BomResponse,
    Cut,
    FramePieceOut,
    GroupCuttingResult,
    GroupedPiece,
    PurchaseOrderLine,
    PurchaseOrderResponse,
    PurchaseOrderSummary,
)

TRADE_LENGTHS_MM = [1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400]

# Mockat pris per löpmeter (SEK), per hållfasthetsklass. Riktiga priser är inte offentligt
# tillgängliga, se docs/prd.md §4.
MOCK_PRICE_PER_METER_SEK = {"C14": 28.0, "C16": 32.0, "C24": 38.0, "GL": 65.0, "CHS": 30.0}
MOCK_LEAD_TIME_DAYS = 5

FRAME_PIECES: list[FramePieceOut] = [
    FramePieceOut(
        oid="589830", item_id="FD5", code="45x182", width_mm=45, height_mm=182,
        length_mm=255.0, mat_code="C24", module_name="131", module_flat="TVÄTT",
        use="ÖPPNINGSREGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589831", item_id="FD4", code="45x182", width_mm=45, height_mm=182,
        length_mm=255.0, mat_code="C24", module_name="131", module_flat="TVÄTT",
        use="ÖPPNINGSREGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589832", item_id="P27", code="45x182", width_mm=45, height_mm=182,
        length_mm=3110.0, mat_code="C24", module_name="131", module_flat="TVÄTT",
        use="MODULREGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589792", item_id="P14", code="45x195", width_mm=45, height_mm=195,
        length_mm=2280.0, mat_code="C24", module_name="132", module_flat="BASTU",
        use="MODULREGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="417827", item_id="1", code="45x45", width_mm=45, height_mm=45,
        length_mm=355.0, mat_code="C16", module_name="130", module_flat="FRD",
        use="REGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="590470", item_id="75", code="45x70", width_mm=45, height_mm=70,
        length_mm=2408.0, mat_code="C24", module_name="131", module_flat="TVÄTT",
        use="REGEL", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589719", item_id="19", code="45x220", width_mm=45, height_mm=220,
        length_mm=3110.2, mat_code="C24", module_name="130", module_flat="FRD",
        use="BÄRLINA", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589965", item_id="2", code="90x220", width_mm=90, height_mm=220,
        length_mm=2781.0, mat_code="C24", module_name="130", module_flat="FRD",
        use="LYFTSTOLPE", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589974", item_id="3", code="45x220", width_mm=45, height_mm=220,
        length_mm=1554.9, mat_code="C16", module_name="130", module_flat="FRD",
        use="BÄRLINA", bom_phase="1. Floor",
    ),
    FramePieceOut(
        oid="589975", item_id="22", code="34x45", width_mm=34, height_mm=45,
        length_mm=1906.0, mat_code="C24", module_name="130", module_flat="FRD",
        use="KORSREGEL", bom_phase="1. Floor",
    ),
]


def get_bom_response() -> BomResponse:
    """OBS: count speglar fixture-listan (10), inte de riktiga 731 -- se docs/plan.md #1."""
    return BomResponse(count=len(FRAME_PIECES), items=FRAME_PIECES)


def _group_key(p: FramePieceOut) -> tuple[str, str]:
    return (p.code, p.mat_code)


def get_bom_groups_response() -> BomGroupsResponse:
    groups: dict[tuple[str, str], list[FramePieceOut]] = {}
    for piece in FRAME_PIECES:
        groups.setdefault(_group_key(piece), []).append(piece)

    return BomGroupsResponse(
        groups=[
            BomGroup(
                code=code,
                mat_code=mat_code,
                piece_count=len(pieces),
                total_length_mm=sum(p.length_mm for p in pieces),
                pieces=[GroupedPiece(oid=p.oid, length_mm=p.length_mm) for p in pieces],
                available_trade_lengths_mm=TRADE_LENGTHS_MM,
            )
            for (code, mat_code), pieces in groups.items()
        ]
    )


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

"""Pydantic-scheman för API-svaren.

Detta är, tillsammans med `docs/api-contract.md`, den bindande kontraktsdefinitionen mellan
backend och frontend (docs/adr.md ADR-1). Ändras ett fält här: uppdatera api-contract.md och
frontend/src/api/types.ts i samma commit.

FastAPI genererar interaktiv dokumentation av dessa scheman på /docs och /openapi.json.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# GET /api/bom  (inkrement 1)
# ---------------------------------------------------------------------------


class FramePieceOut(BaseModel):
    """En rad i materialbehovslistan, motsvarar en <FRAMEPIECE> i components.xml."""

    oid: str = Field(..., description="FRAMEPIECE OID. Matchar IFCBEAM.Tag i .ifc-filen 1:1.")
    item_id: str | None = Field(None, description="Vertex BD ITEM_ID, t.ex. 'FD5'.")
    code: str = Field(..., description="Tvärsnittskod, t.ex. '45x182'.")
    width_mm: float = Field(
        ..., description="WIDTH, mm. Oftast heltal, men enstaka SHIMS-poster (MAT_CODE=C14) har decimaler."
    )
    height_mm: int = Field(..., description="HEIGHT, mm.")
    length_mm: float = Field(..., description="Kaplängd, LENGTH, mm.")
    mat_code: str = Field(..., description="Hållfasthetsklass, t.ex. C24, C16, C14, GL.")
    module_name: str | None = Field(None, description="MODULE_NAME, modul-/rumsnummer.")
    module_flat: str | None = Field(None, description="MODULE_FLAT, modulens namn/rum.")
    use: str = Field(..., description="Funktion, t.ex. ÖPPNINGSREGEL, MODULREGEL, BÄRLINA.")
    bom_phase: str | None = Field(None, description="BOM_PHASE, t.ex. '1. Floor'.")


class BomResponse(BaseModel):
    count: int = Field(..., description="Antal poster i items (731 för fullt facit).")
    items: list[FramePieceOut]


# ---------------------------------------------------------------------------
# GET /api/bom/groups  (inkrement 2)
# ---------------------------------------------------------------------------


class GroupedPiece(BaseModel):
    oid: str
    length_mm: float


class BomGroup(BaseModel):
    """Materialbehov grupperat per (tvärsnitt, materialklass), matchat mot handelslängder."""

    code: str = Field(..., description="Tvärsnittskod, t.ex. '45x182'.")
    mat_code: str = Field(..., description="Hållfasthetsklass, t.ex. 'C24'.")
    piece_count: int = Field(..., description="Antal kapbitar i gruppen.")
    total_length_mm: float = Field(..., description="Summa kaplängder i gruppen, mm.")
    pieces: list[GroupedPiece]
    available_trade_lengths_mm: list[int] = Field(
        ..., description="Handelslängder från data/svensktra_standardlangder_mm.csv."
    )


class BomGroupsResponse(BaseModel):
    groups: list[BomGroup]


# ---------------------------------------------------------------------------
# GET /api/purchase-order  (inkrement 3, underlag för inkrement 4)
# ---------------------------------------------------------------------------


class Cut(BaseModel):
    """En kapbit skuren ur en inköpt stång. `oid` är nyckeln för 3D-highlight (inkrement 4).

    Om kapbiten är längre än längsta handelslängden (docs/prd.md §0/§3.3) täcks den av flera
    `Cut`-rader (en per inköpt stång den är skarvad ur) med `spliced=True` och
    `segment_index`/`segment_count` satta — se `GroupCuttingResult.splices` för aggregatet.
    """

    oid: str
    length_mm: float
    spliced: bool = Field(False, description="True om detta bara är ett segment av kapbiten.")
    segment_index: int | None = Field(
        None, description="1-baserat segmentnummer, satt endast när spliced=True."
    )
    segment_count: int | None = Field(
        None, description="Totalt antal segment kapbiten är byggd av, satt endast när spliced=True."
    )


class Bar(BaseModel):
    """En inköpt stång (handelslängd) och hur den kapas."""

    purchase_length_mm: int
    cuts: list[Cut]
    used_length_mm: float = Field(..., description="Summa kaplängder + kerf på denna stång.")
    kerf_total_mm: float = Field(..., description="Antal snitt * KERF_MM på denna stång.")
    waste_mm: float = Field(..., description="purchase_length_mm - used_length_mm.")


class Splice(BaseModel):
    """Aggregat för en kapbit (`oid`) som är skarvad ur flera inköpta längder.

    Validerar bara materialtäckning/spill, inte var skarven strukturellt får sitta
    (docs/prd.md §4, medveten avgränsning). Ingen extra kerf modelleras för skarven själv —
    varje segments kerf räknas redan i dess `Bar.kerf_total_mm`.
    """

    oid: str
    total_length_mm: float = Field(..., description="Kapbitens fulla behovslängd, samma som i /api/bom.")
    segment_count: int
    purchase_lengths_mm: list[int] = Field(..., description="Inköpta längder biten byggs av.")
    joint_count: int = Field(..., description="segment_count - 1.")


class GroupCuttingResult(BaseModel):
    code: str
    mat_code: str
    waste_percent: float
    algorithm: Literal["greedy", "exact"] = Field(
        "greedy", description="Vilket läge gruppen kördes med, se docs/adr.md ADR-2-tillägget."
    )
    optimal: bool = Field(
        True,
        description=(
            "True om lösningen är bevisat optimal (alltid True för greedy; för exact bara True "
            "om CP-SAT löste till bevisad optimalitet inom tidsgränsen, annars 'bästa hittade')."
        ),
    )
    solve_time_ms: float = Field(0.0, description="Lösningstid för gruppen, ms.")
    bars: list[Bar]
    splices: list[Splice] = Field(
        default_factory=list, description="En rad per skarvat oid i gruppen."
    )


class PurchaseOrderLine(BaseModel):
    """En rad i det granskningsbara inköpsunderlaget (docs/prd.md §3.5)."""

    code: str
    mat_code: str
    purchase_length_mm: int
    quantity: int
    article_number: str = Field(..., description="Mockad artikelbeteckning, se docs/prd.md §4.")
    price_per_unit_sek: float = Field(..., description="Mockat pris.")
    lead_time_days: int = Field(..., description="Mockad leveranstid.")
    total_price_sek: float


class PurchaseOrderSummary(BaseModel):
    total_bars: int
    total_needed_length_mm: float
    total_purchased_length_mm: float
    total_waste_percent: float
    total_cost_sek: float
    spliced_piece_count: int = Field(0, description="Antal oid som behövde skarvas.")
    total_joints: int = Field(0, description="Summa joint_count över alla splices.")


class PurchaseOrderResponse(BaseModel):
    kerf_mm: float
    algorithm: Literal["greedy", "exact"] = Field(
        "greedy", description="Ekar tillbaka query-parametern ?algorithm= (docs/adr.md ADR-2-tillägget)."
    )
    groups: list[GroupCuttingResult]
    order_lines: list[PurchaseOrderLine]
    summary: PurchaseOrderSummary

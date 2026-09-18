"""Kapoptimering (1D cutting stock) per grupp, plus inköpsunderlag och spillrapport.

Inkrement 3, docs/plan.md rad 3. Algoritm: girig First-Fit-Decreasing, INTE en exakt
ILP-lösare — det beslutet står i docs/adr.md ADR-2 och ändras inte här.
"""

from app.models import BomGroup, GroupCuttingResult, PurchaseOrderLine, PurchaseOrderSummary


def optimize_group(group: BomGroup, kerf_mm: float) -> GroupCuttingResult:
    """Kör FFD mot group.available_trade_lengths_mm, kerf_mm avdrag per snitt.

    Sortera kaplängderna fallande, packa girigt i den kortaste handelslängd som får plats,
    öppna en ny stång annars.

    Kontroll (docs/plan.md #3): för en given grupp balanserar materialet, dvs.
    sum(cuts.length_mm) + kerf_total_mm + waste_mm == used_length_mm <= purchase_length_mm
    på varje stång.
    """
    raise NotImplementedError("Inkrement 3, se docs/plan.md rad 3")


def build_order_lines(results: list[GroupCuttingResult]) -> list[PurchaseOrderLine]:
    """Aggregera bars till inköpsrader och slå på mockat pris/artikelnr/leveranstid.

    Riktiga priser/artikelnummer finns inte öppet tillgängliga (docs/prd.md §4) — mocka en
    liten statisk katalog, t.ex. kr/löpmeter per mat_code.
    """
    raise NotImplementedError("Inkrement 3, se docs/plan.md rad 3")


def build_summary(results: list[GroupCuttingResult], order_lines: list[PurchaseOrderLine]) -> PurchaseOrderSummary:
    """Summera total spillprocent, total kostnad, totalt antal stänger m.m."""
    raise NotImplementedError("Inkrement 3, se docs/plan.md rad 3")

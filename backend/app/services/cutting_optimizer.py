"""Kapoptimering (1D cutting stock) per grupp, plus inköpsunderlag och spillrapport.

Inkrement 3, docs/plan.md rad 3. Standardalgoritm: girig First-Fit-Decreasing (docs/adr.md
ADR-2). En exakt lösare (OR-Tools CP-SAT) finns som valbart alternativ (algorithm="exact"),
se ADR-2-tillägget -- girig FFD förblir standard och dess beteende är oförändrat.
"""

import math
import time
from typing import Literal

from app.config import EXACT_SOLVER_NUM_WORKERS
from app.models import (
    Bar,
    BomGroup,
    Cut,
    GroupCuttingResult,
    GroupedPiece,
    PurchaseOrderLine,
    PurchaseOrderSummary,
    Splice,
)

# Mockat pris per löpmeter (SEK), per hållfasthetsklass. Riktiga priser är inte offentligt
# tillgängliga, se docs/prd.md §4.
MOCK_PRICE_PER_METER_SEK = {"C14": 28.0, "C16": 32.0, "C24": 38.0, "GL": 65.0}
DEFAULT_PRICE_PER_METER_SEK = 30.0
MOCK_LEAD_TIME_DAYS = 5


def _pack_ffd(pieces: list[GroupedPiece], trade_lengths_asc: list[int], kerf_mm: float) -> list[Bar]:
    """Klassisk First-Fit-Decreasing.

    Sortera kaplängderna fallande. Testa öppna stänger i den ordning de öppnades (first-fit);
    får biten inte plats i någon, öppna en ny stång i den minsta handelslängd som räcker
    (minimerar spillet på den nya stången).
    """
    open_bars: list[dict] = []

    for piece in sorted(pieces, key=lambda p: p.length_mm, reverse=True):
        needed = piece.length_mm + kerf_mm
        bar = next(
            (b for b in open_bars if b["purchase_length_mm"] - b["used_length_mm"] >= needed),
            None,
        )
        if bar is None:
            purchase_length_mm = next((t for t in trade_lengths_asc if t >= needed), None)
            if purchase_length_mm is None:
                raise ValueError(
                    f"Ingen handelslängd rymmer stycket {piece.oid} "
                    f"({piece.length_mm} mm + kerf {kerf_mm} mm)"
                )
            bar = {"purchase_length_mm": purchase_length_mm, "cuts": [], "used_length_mm": 0.0}
            open_bars.append(bar)

        bar["cuts"].append(Cut(oid=piece.oid, length_mm=piece.length_mm))
        bar["used_length_mm"] += needed

    return [
        Bar(
            purchase_length_mm=b["purchase_length_mm"],
            cuts=b["cuts"],
            used_length_mm=b["used_length_mm"],
            kerf_total_mm=len(b["cuts"]) * kerf_mm,
            waste_mm=b["purchase_length_mm"] - b["used_length_mm"],
        )
        for b in open_bars
    ]


def _solve_exact(
    pieces: list[GroupedPiece], trade_lengths_asc: list[int], kerf_mm: float, time_budget_s: float
) -> tuple[list[Bar], bool]:
    """Exakt bin packing (OR-Tools CP-SAT), variabel stånglängd -- minimerar total inköpt längd.

    Se docs/adr.md ADR-2-tillägget för bakgrund och uppmätta spilltal (ursprungligen mätt i
    backend/spikes/exact_cutting_spike.py). Övre gräns på antal stänger sätts av en girig
    FFD-körning (säker, om än onödigt stor, gräns). Returnerar (bars, optimal) där optimal bara
    är True om lösaren bevisade optimalitet inom time_budget_s -- annars "bästa hittade", och vi
    faller tillbaka på FFD-lösningen om ingen lösning alls hittades inom tidsgränsen.
    """
    from ortools.sat.python import cp_model

    baseline_bars = _pack_ffd(pieces, trade_lengths_asc, kerf_mm)
    if not pieces:
        return baseline_bars, True

    model = cp_model.CpModel()
    n = len(pieces)
    max_bins = len(baseline_bars)

    domain = cp_model.Domain.FromValues([0] + trade_lengths_asc)
    capacity = [model.NewIntVarFromDomain(domain, f"cap_{j}") for j in range(max_bins)]
    assign = [[model.NewBoolVar(f"x_{i}_{j}") for j in range(max_bins)] for i in range(n)]

    for i in range(n):
        model.Add(sum(assign[i][j] for j in range(max_bins)) == 1)

    # Avrunda uppåt, inte till närmaste heltal: CP-SAT:s heltalsdomän måste alltid vara en
    # konservativ övre gräns på det riktiga (flyttals-)behovet, annars kan den verkliga summan
    # (piece.length_mm + kerf) hamna över purchase_length_mm trots att modellen tillåter den.
    needed = [math.ceil(p.length_mm + kerf_mm) for p in pieces]
    for j in range(max_bins):
        model.Add(sum(needed[i] * assign[i][j] for i in range(n)) <= capacity[j])

    # Symmetribrytning: kapacitet fallande -- färre ekvivalenta permutationer att utforska.
    for j in range(max_bins - 1):
        model.Add(capacity[j] >= capacity[j + 1])

    model.Minimize(sum(capacity))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_budget_s
    solver.parameters.num_workers = EXACT_SOLVER_NUM_WORKERS
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return baseline_bars, False

    bars: list[Bar] = []
    for j in range(max_bins):
        purchase_length_mm = solver.Value(capacity[j])
        if purchase_length_mm == 0:
            continue

        bin_pieces = [pieces[i] for i in range(n) if solver.Value(assign[i][j])]
        cuts = [Cut(oid=p.oid, length_mm=p.length_mm) for p in bin_pieces]
        used_length_mm = sum(p.length_mm for p in bin_pieces) + len(bin_pieces) * kerf_mm
        bars.append(
            Bar(
                purchase_length_mm=purchase_length_mm,
                cuts=cuts,
                used_length_mm=used_length_mm,
                kerf_total_mm=len(bin_pieces) * kerf_mm,
                waste_mm=purchase_length_mm - used_length_mm,
            )
        )

    return bars, status == cp_model.OPTIMAL


def _splice_piece(
    piece: GroupedPiece, trade_lengths_desc: list[int], kerf_mm: float
) -> tuple[list[Bar], Splice]:
    """Skarva ett behov längre än längsta handelslängden över flera inköpta stänger.

    Störst först (docs/adr.md ADR-2, skarvning): fyll hela stänger av den längsta
    handelslängden tills resten ryms i en enda stång, välj då den minsta handelslängd som
    räcker -- minimerar spillet på sista segmentet. Varje segment blir en egen, dedikerad
    stång (delar inte plats med andra bitars kap) -- se docs/api-contract.md exempel.
    """
    max_trade = trade_lengths_desc[0]
    remaining = piece.length_mm
    segments: list[tuple[int, float]] = []

    while remaining > max_trade - kerf_mm:
        segments.append((max_trade, max_trade - kerf_mm))
        remaining -= max_trade - kerf_mm

    best_fit = min((t for t in trade_lengths_desc if t - kerf_mm >= remaining), default=max_trade)
    segments.append((best_fit, remaining))

    segment_count = len(segments)
    bars = [
        Bar(
            purchase_length_mm=purchase_length_mm,
            cuts=[
                Cut(
                    oid=piece.oid,
                    length_mm=cut_length,
                    spliced=True,
                    segment_index=index + 1,
                    segment_count=segment_count,
                )
            ],
            used_length_mm=cut_length + kerf_mm,
            kerf_total_mm=kerf_mm,
            waste_mm=purchase_length_mm - (cut_length + kerf_mm),
        )
        for index, (purchase_length_mm, cut_length) in enumerate(segments)
    ]

    splice = Splice(
        oid=piece.oid,
        total_length_mm=piece.length_mm,
        segment_count=segment_count,
        purchase_lengths_mm=[purchase_length_mm for purchase_length_mm, _ in segments],
        joint_count=segment_count - 1,
    )
    return bars, splice


def optimize_group(
    group: BomGroup,
    kerf_mm: float,
    algorithm: Literal["greedy", "exact"] = "greedy",
    time_budget_s: float = 0.0,
) -> GroupCuttingResult:
    """Packa mot group.available_trade_lengths_mm, kerf_mm avdrag per snitt.

    algorithm="greedy" (default, docs/adr.md ADR-2): girig First-Fit-Decreasing, alltid
    optimal=True (gör inget optimalitetsanspråk men har heller ingen tidsgräns att missa).
    algorithm="exact" (ADR-2-tillägget): OR-Tools CP-SAT med time_budget_s per grupp --
    optimal=True bara om lösaren bevisade optimalitet inom tidsgränsen.

    Behov längre än längsta handelslängden skarvas (docs/prd.md §0/§3.3) istället för att
    packas, oavsett algorithm -- se _splice_piece.

    Kontroll (docs/plan.md #3): för en given grupp balanserar materialet, dvs.
    sum(cuts.length_mm) + kerf_total_mm + waste_mm == used_length_mm <= purchase_length_mm
    på varje stång.
    """
    trade_lengths_asc = sorted(group.available_trade_lengths_mm)
    trade_lengths_desc = list(reversed(trade_lengths_asc))
    max_trade = trade_lengths_desc[0]

    normal_pieces = [p for p in group.pieces if p.length_mm <= max_trade]
    long_pieces = [p for p in group.pieces if p.length_mm > max_trade]

    start = time.perf_counter()
    if algorithm == "exact":
        bars, optimal = _solve_exact(normal_pieces, trade_lengths_asc, kerf_mm, time_budget_s)
    else:
        bars = _pack_ffd(normal_pieces, trade_lengths_asc, kerf_mm)
        optimal = True
    solve_time_ms = (time.perf_counter() - start) * 1000

    splices: list[Splice] = []
    for piece in long_pieces:
        splice_bars, splice = _splice_piece(piece, trade_lengths_desc, kerf_mm)
        bars.extend(splice_bars)
        splices.append(splice)

    total_purchased = sum(bar.purchase_length_mm for bar in bars)
    total_waste = sum(bar.waste_mm for bar in bars)
    waste_percent = round(100 * total_waste / total_purchased, 2) if total_purchased else 0.0

    return GroupCuttingResult(
        code=group.code,
        mat_code=group.mat_code,
        waste_percent=waste_percent,
        algorithm=algorithm,
        optimal=optimal,
        solve_time_ms=round(solve_time_ms, 2),
        bars=bars,
        splices=splices,
    )


def build_order_lines(results: list[GroupCuttingResult]) -> list[PurchaseOrderLine]:
    """Aggregera bars till inköpsrader och slå på mockat pris/artikelnr/leveranstid.

    Riktiga priser/artikelnummer finns inte öppet tillgängliga (docs/prd.md §4) — mocka en
    liten statisk katalog, kr/löpmeter per mat_code.
    """
    counts: dict[tuple[str, str, int], int] = {}
    for result in results:
        for bar in result.bars:
            key = (result.code, result.mat_code, bar.purchase_length_mm)
            counts[key] = counts.get(key, 0) + 1

    order_lines = []
    for (code, mat_code, purchase_length_mm), quantity in sorted(counts.items()):
        price_per_meter = MOCK_PRICE_PER_METER_SEK.get(mat_code, DEFAULT_PRICE_PER_METER_SEK)
        price_per_unit_sek = round(purchase_length_mm / 1000 * price_per_meter, 2)
        order_lines.append(
            PurchaseOrderLine(
                code=code,
                mat_code=mat_code,
                purchase_length_mm=purchase_length_mm,
                quantity=quantity,
                article_number=f"MOCK-{code}-{mat_code}-{purchase_length_mm}",
                price_per_unit_sek=price_per_unit_sek,
                lead_time_days=MOCK_LEAD_TIME_DAYS,
                total_price_sek=round(price_per_unit_sek * quantity, 2),
            )
        )
    return order_lines


def build_summary(
    results: list[GroupCuttingResult], order_lines: list[PurchaseOrderLine]
) -> PurchaseOrderSummary:
    """Summera total spillprocent, total kostnad, totalt antal stänger m.m."""
    total_bars = sum(len(r.bars) for r in results)
    total_needed_length_mm = sum(cut.length_mm for r in results for bar in r.bars for cut in bar.cuts)
    total_purchased_length_mm = sum(bar.purchase_length_mm for r in results for bar in r.bars)
    total_waste_mm = sum(bar.waste_mm for r in results for bar in r.bars)
    total_waste_percent = (
        round(100 * total_waste_mm / total_purchased_length_mm, 2) if total_purchased_length_mm else 0.0
    )

    return PurchaseOrderSummary(
        total_bars=total_bars,
        total_needed_length_mm=total_needed_length_mm,
        total_purchased_length_mm=float(total_purchased_length_mm),
        total_waste_percent=total_waste_percent,
        total_cost_sek=round(sum(line.total_price_sek for line in order_lines), 2),
        spliced_piece_count=sum(len(r.splices) for r in results),
        total_joints=sum(s.joint_count for r in results for s in r.splices),
    )

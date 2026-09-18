"""SPIKE, inte produktionskod: jämför nuvarande giriga FFD (docs/adr.md ADR-2) mot en exakt
lösare (OR-Tools CP-SAT) för kapoptimeringen. Syftet är att ta fram ett konkret tal på hur
mycket spill vi faktiskt skulle vinna, innan vi eventuellt uppdaterar ADR-2 och byter algoritm
i backend/app/services/cutting_optimizer.py.

Körs fristående, importerar bara riktiga produktionsfunktioner (ingen egen datamodell):
    cd backend && .venv/bin/python spikes/exact_cutting_spike.py [CODE] [MAT_CODE] [tidsgräns_s]

Default: gruppen 45x182/C24 (72 bitar, samma som används som exempel i docs/api-contract.md),
60 sekunders tidsgräns.

Skarvade bitar (> längsta handelslängden) lämnas orörda -- samma _splice_piece som idag, det
är bara den "normala" bin-packing-delen (girig FFD vs. exakt) som jämförs här, se ADR-2:s
ursprungliga omfattning.

Detta var det ursprungliga spiket bakom ADR-2-tillägget (valbar exakt lösare). Den riktiga
implementationen ligger nu i app/services/cutting_optimizer.py (_solve_exact) och nås via
GET /api/purchase-order?algorithm=exact -- ortools är sedan dess ett riktigt beroende i
backend/requirements.txt. Skriptet här lever kvar som ett fristående jämförelseverktyg.
"""

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ortools.sat.python import cp_model

from app.config import KERF_MM
from app.services.article_matching import get_trade_lengths_mm, group_by_code_and_material
from app.services.cutting_optimizer import _pack_ffd
from app.services.xml_parser import get_frame_pieces


def solve_exact(pieces, trade_lengths_asc, kerf_mm, time_limit_s):
    """Exakt bin-packing med variabel stånglängd (CP-SAT). Minimerar total inköpt längd,
    inte bara antal stänger -- det är rätt proxy för kostnad/spill när priset är kr/löpmeter.
    """
    model = cp_model.CpModel()
    n = len(pieces)

    # Övre gräns på antal stänger: en girig FFD-körning ger en säker (om än onödigt stor)
    # gräns -- aldrig fler stänger än vad girig redan klarar sig med.
    baseline_bars = _pack_ffd(pieces, trade_lengths_asc, kerf_mm)
    max_bins = len(baseline_bars)

    domain = cp_model.Domain.FromValues([0] + trade_lengths_asc)
    capacity = [model.NewIntVarFromDomain(domain, f"cap_{j}") for j in range(max_bins)]
    assign = [[model.NewBoolVar(f"x_{i}_{j}") for j in range(max_bins)] for i in range(n)]

    for i in range(n):
        model.Add(sum(assign[i][j] for j in range(max_bins)) == 1)

    # Avrunda uppåt (inte till närmaste heltal), samma fix som i den riktiga
    # _solve_exact i app/services/cutting_optimizer.py -- annars kan CP-SAT:s heltalsdomän
    # tillåta en riktig (flyttals-)summa som faktiskt överstiger purchase_length_mm.
    needed = [math.ceil(p.length_mm + kerf_mm) for p in pieces]
    for j in range(max_bins):
        model.Add(sum(needed[i] * assign[i][j] for i in range(n)) <= capacity[j])

    # Symmetribrytning: kapacitet fallande -- färre ekvivalenta permutationer att utforska.
    for j in range(max_bins - 1):
        model.Add(capacity[j] >= capacity[j + 1])

    model.Minimize(sum(capacity))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    bars = []
    for j in range(max_bins):
        cap = solver.Value(capacity[j])
        if cap == 0:
            continue
        cuts = [pieces[i] for i in range(n) if solver.Value(assign[i][j])]
        bars.append((cap, cuts))

    return {
        "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE (tidsgräns nådd)",
        "bars": bars,
        "total_purchased_mm": sum(cap for cap, _ in bars),
    }


def waste_percent(total_purchased_mm, needed_mm):
    return round(100 * (total_purchased_mm - needed_mm) / total_purchased_mm, 2)


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "45x182"
    mat_code = sys.argv[2] if len(sys.argv) > 2 else "C24"
    time_limit_s = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0

    trade_lengths_asc = sorted(get_trade_lengths_mm())
    max_trade = trade_lengths_asc[-1]
    groups = group_by_code_and_material(get_frame_pieces(), trade_lengths_asc)
    group = next(g for g in groups if g.code == code and g.mat_code == mat_code)

    normal_pieces = [p for p in group.pieces if p.length_mm <= max_trade]
    long_pieces = [p for p in group.pieces if p.length_mm > max_trade]
    needed_mm = sum(p.length_mm for p in normal_pieces)

    print(f"Grupp {code}/{mat_code}: {len(group.pieces)} bitar totalt "
          f"({len(normal_pieces)} normala, {len(long_pieces)} skarvas -- oförändrat, ej med i jämförelsen)")
    print(f"Behovslängd (normala bitar): {needed_mm:.1f} mm, kerf={KERF_MM} mm\n")

    t0 = time.time()
    ffd_bars = _pack_ffd(normal_pieces, trade_lengths_asc, KERF_MM)
    ffd_total = sum(b.purchase_length_mm for b in ffd_bars)
    ffd_time = time.time() - t0
    print(f"Girig FFD (nuvarande, ADR-2):  {len(ffd_bars):3d} stänger, "
          f"{ffd_total:8.0f} mm inköpt, spill {waste_percent(ffd_total, needed_mm):5.2f}%  "
          f"({ffd_time * 1000:.1f} ms)")

    t0 = time.time()
    result = solve_exact(normal_pieces, trade_lengths_asc, KERF_MM, time_limit_s)
    exact_time = time.time() - t0
    if result is None:
        print(f"Exakt (CP-SAT):                ingen lösning inom {time_limit_s:.0f}s tidsgräns")
        return

    print(f"Exakt (CP-SAT, {result['status']:>24s}): {len(result['bars']):3d} stänger, "
          f"{result['total_purchased_mm']:8.0f} mm inköpt, "
          f"spill {waste_percent(result['total_purchased_mm'], needed_mm):5.2f}%  "
          f"({exact_time:.1f} s)")

    saved_mm = ffd_total - result["total_purchased_mm"]
    print(f"\nBesparing exakt vs. girig: {saved_mm:.0f} mm "
          f"({100 * saved_mm / ffd_total:.2f}% av girigs inköpta längd)")


if __name__ == "__main__":
    main()

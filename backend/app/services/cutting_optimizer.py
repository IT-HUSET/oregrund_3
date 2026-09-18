"""Kapoptimering (1D cutting stock) per grupp, plus inköpsunderlag och spillrapport.

Inkrement 3, docs/plan.md rad 3. Algoritm: girig First-Fit-Decreasing, INTE en exakt
ILP-lösare — det beslutet står i docs/adr.md ADR-2 och ändras inte här.

Konventioner (data/dataspec.md §9 punkt 3, avgjort):
- Ett kerf-avdrag per kapad bit (inte per bit - 1). Varje bit kostar alltså sin egen längd
  plus KERF_MM på stången den skärs ur. Konservativt och enkelt att förklara vid sågen.
- Kerf-värdet självt bor i app/config.py::KERF_MM (3.0 mm), inte hårdkodat här.
"""

from app.config import KERF_MM
from app.models import (
    Bar,
    Baseline,
    BomGroup,
    Cut,
    GroupCuttingResult,
    GroupedPiece,
    PurchaseOrderLine,
    PurchaseOrderSummary,
    Splice,
)

#: Mockat pris per löpmeter (SEK) per hållfasthetsklass. Riktiga priser är inte offentligt
#: tillgängliga (docs/prd.md §4) — bara handelslängderna är riktig data.
MOCK_PRICE_PER_METER_SEK = {"C14": 28.0, "C16": 32.0, "C24": 38.0, "GL": 65.0}
MOCK_DEFAULT_PRICE_PER_METER_SEK = 30.0
MOCK_LEAD_TIME_DAYS = 5


def article_number(code: str, mat_code: str, purchase_length_mm: int) -> str:
    """Mockad artikelbeteckning (docs/prd.md §4). Stabil nyckel för inköpsraderna."""
    return f"MOCK-{code}-{mat_code}-{purchase_length_mm}"


def _price_per_unit_sek(mat_code: str, purchase_length_mm: int) -> float:
    per_meter = MOCK_PRICE_PER_METER_SEK.get(mat_code, MOCK_DEFAULT_PRICE_PER_METER_SEK)
    return round(purchase_length_mm / 1000 * per_meter, 2)


class _OpenBar:
    """En påbörjad stång under packningen. Blir en `Bar` i svaret när gruppen är klar."""

    def __init__(self, purchase_length_mm: int) -> None:
        self.purchase_length_mm = purchase_length_mm
        self.cuts: list[Cut] = []
        self.used_length_mm = 0.0
        self.kerf_total_mm = 0.0

    def remaining_mm(self) -> float:
        return self.purchase_length_mm - self.used_length_mm

    def fits(self, length_mm: float, kerf_mm: float) -> bool:
        # +1e-9: flyttalsmarginal, kaplängderna har max 1 decimal (data/dataspec.md §3.2).
        return length_mm + kerf_mm <= self.remaining_mm() + 1e-9

    def place(self, cut: Cut, kerf_mm: float) -> None:
        self.cuts.append(cut)
        self.used_length_mm = round(self.used_length_mm + cut.length_mm + kerf_mm, 6)
        self.kerf_total_mm = round(self.kerf_total_mm + kerf_mm, 6)

    def to_bar(self) -> Bar:
        return Bar(
            purchase_length_mm=self.purchase_length_mm,
            cuts=self.cuts,
            used_length_mm=round(self.used_length_mm, 3),
            kerf_total_mm=round(self.kerf_total_mm, 3),
            waste_mm=round(self.purchase_length_mm - self.used_length_mm, 3),
        )


def _split_oversized(
    piece: GroupedPiece, trade_lengths_mm: list[int], kerf_mm: float
) -> tuple[list[float], list[int]]:
    """Dela en kapbit som är längre än längsta handelslängden i skarvbara segment.

    docs/prd.md §0/§3.3, docs/adr.md ADR-2 (tillägg): girigt, största handelslängden först,
    tills återstoden får plats i en enskild längd. Returnerar (segmentlängder, de
    handelslängder segmenten är tänkta att skäras ur). Segmentlängderna summerar exakt till
    kapbitens behovslängd — ingen extra kerf modelleras för själva skarven, se docs/prd.md §3.3.

    Algoritmen optimerar bara materialtäckning/spill. Var skarven strukturellt får sitta
    valideras INTE (docs/prd.md §4, medveten avgränsning) — raderna flaggas spliced=True för
    manuell konstruktörsgranskning.
    """
    longest = trade_lengths_mm[-1]
    # En stång rymmer handelslängden minus ett kerf — det är den verkliga kapaciteten.
    max_segment = longest - kerf_mm
    segments: list[float] = []
    planned_lengths: list[int] = []
    remaining = piece.length_mm

    while remaining > max_segment + 1e-9:
        # Fyll en hel längsta stång; kerf för det snittet ryms i stången, inte i behovslängden.
        segments.append(round(max_segment, 3))
        planned_lengths.append(longest)
        remaining = round(remaining - max_segment, 3)

    # Sista segmentet: kortaste handelslängd som rymmer resten + kerf.
    final = next(
        (length for length in trade_lengths_mm if remaining + kerf_mm <= length + 1e-9),
        longest,
    )
    segments.append(round(remaining, 3))
    planned_lengths.append(final)
    return segments, planned_lengths


def _choose_new_bar_length(
    cut: Cut, remaining: list[Cut], trade_lengths_mm: list[int], kerf_mm: float
) -> int:
    """Välj handelslängd när en ny stång öppnas för `cut`.

    Ren FFD tar kortaste längd som rymmer biten — men eftersom längden låses när stången
    öppnas straffar det efterföljande bitar: 1200+900+600 hamnar då i 1800+1800 mm (25 % spill)
    i stället för en enda 3000 mm-stång (9,7 %). Vi provar därför varje handelslängd som rymmer
    biten, simulerar girigt vad som skulle få plats med i samma stång, och väljer den längd som
    ger minst spill (vid lika: den kortaste).

    Detta är fortfarande en girig heuristik, inte en exakt lösare (docs/adr.md ADR-2) — bara ett
    lookahead på den stång som öppnas just nu.
    """
    candidates = [
        length for length in trade_lengths_mm if cut.length_mm + kerf_mm <= length + 1e-9
    ]
    if not candidates:
        return trade_lengths_mm[-1]

    best_length = candidates[0]
    best_waste: float | None = None

    for length in candidates:
        free = length - (cut.length_mm + kerf_mm)
        for other in remaining:
            if other.length_mm + kerf_mm <= free + 1e-9:
                free -= other.length_mm + kerf_mm
        if best_waste is None or free < best_waste - 1e-9:
            best_waste = free
            best_length = length

    return best_length


def optimize_group(group: BomGroup, kerf_mm: float) -> GroupCuttingResult:
    """Kör FFD mot group.available_trade_lengths_mm, kerf_mm avdrag per snitt.

    Sortera kaplängderna fallande, packa girigt i den kortaste handelslängd som får plats,
    öppna en ny stång annars.

    Kontroll (docs/plan.md #3): för en given grupp balanserar materialet, dvs.
    sum(cuts.length_mm) + kerf_total_mm + waste_mm == used_length_mm <= purchase_length_mm
    på varje stång.
    """
    trade_lengths_mm = sorted(group.available_trade_lengths_mm)
    if not trade_lengths_mm:
        raise ValueError(f"Gruppen {group.code}/{group.mat_code} saknar handelslängder")

    longest = trade_lengths_mm[-1]
    # Kapbiten måste rymmas i längsta stången TILLSAMMANS med sitt kerf, annars måste den
    # skarvas — jämför alltså mot longest - kerf, inte mot longest (annars kan en bit på
    # t.ex. 5398 mm hamna i en 5400-stång och ge negativt spill).
    max_single_piece_mm = longest - kerf_mm

    # 1. Dela överlånga behov i skarvsegment innan packningen (docs/adr.md ADR-2, tillägg).
    #    Ett segment packas sedan precis som vilken kapbit som helst, fast flaggat.
    demands: list[Cut] = []
    splices: list[Splice] = []
    for piece in group.pieces:
        if piece.length_mm <= max_single_piece_mm + 1e-9:
            demands.append(Cut(oid=piece.oid, length_mm=piece.length_mm))
            continue

        segments, planned_lengths = _split_oversized(piece, trade_lengths_mm, kerf_mm)
        for index, segment in enumerate(segments, start=1):
            demands.append(
                Cut(
                    oid=piece.oid,
                    length_mm=segment,
                    spliced=True,
                    segment_index=index,
                    segment_count=len(segments),
                )
            )
        splices.append(
            Splice(
                oid=piece.oid,
                total_length_mm=piece.length_mm,
                segment_count=len(segments),
                purchase_lengths_mm=planned_lengths,
                joint_count=len(segments) - 1,
            )
        )

    # 2. First-Fit-Decreasing: längsta behovet först, i första stången där det får plats.
    demands.sort(key=lambda cut: (-cut.length_mm, cut.oid))

    bars: list[_OpenBar] = []
    for index, cut in enumerate(demands):
        target = next((bar for bar in bars if bar.fits(cut.length_mm, kerf_mm)), None)
        if target is None:
            purchase_length = _choose_new_bar_length(
                cut, demands[index + 1 :], trade_lengths_mm, kerf_mm
            )
            target = _OpenBar(purchase_length)
            bars.append(target)
        target.place(cut, kerf_mm)

    # 3. Krymp varje stång till kortaste handelslängd som fortfarande rymmer innehållet.
    #    FFD väljer längd när stången öppnas; efteråt vet vi hur mycket som faktiskt användes.
    for bar in bars:
        bar.purchase_length_mm = next(
            (length for length in trade_lengths_mm if bar.used_length_mm <= length + 1e-9),
            bar.purchase_length_mm,
        )

    finished = [bar.to_bar() for bar in bars]

    # Skarvraderna måste spegla de stänger segmenten FAKTISKT hamnade i. planned_lengths ovan
    # är bara en uppskattning gjord före packningen; FFD och krympsteget flyttar ofta ett
    # segment till en annan handelslängd. Rapporterar vi planen i stället för utfallet säger
    # underlaget att en 4500-stång behövs när en 5400 köptes (docs/prd.md §3.5: granskningsbart).
    for splice in splices:
        splice.purchase_lengths_mm = [
            bar.purchase_length_mm
            for bar in finished
            for cut in bar.cuts
            if cut.oid == splice.oid
        ]
    purchased_mm = sum(bar.purchase_length_mm for bar in finished)
    needed_mm = sum(cut.length_mm for bar in finished for cut in bar.cuts)
    waste_percent = round((purchased_mm - needed_mm) / purchased_mm * 100, 2) if purchased_mm else 0.0

    # Stabil, läsbar ordning i UI:t: längsta stången först.
    finished.sort(key=lambda bar: (-bar.purchase_length_mm, -bar.used_length_mm))

    return GroupCuttingResult(
        code=group.code,
        mat_code=group.mat_code,
        waste_percent=waste_percent,
        bars=finished,
        splices=sorted(splices, key=lambda s: s.oid),
    )


def build_order_lines(results: list[GroupCuttingResult]) -> list[PurchaseOrderLine]:
    """Aggregera bars till inköpsrader och slå på mockat pris/artikelnr/leveranstid.

    Riktiga priser/artikelnummer finns inte öppet tillgängliga (docs/prd.md §4) — mocka en
    liten statisk katalog, t.ex. kr/löpmeter per mat_code.
    """
    quantities: dict[tuple[str, str, int], int] = {}
    for result in results:
        for bar in result.bars:
            key = (result.code, result.mat_code, bar.purchase_length_mm)
            quantities[key] = quantities.get(key, 0) + 1

    lines = []
    for (code, mat_code, purchase_length_mm), quantity in quantities.items():
        price = _price_per_unit_sek(mat_code, purchase_length_mm)
        lines.append(
            PurchaseOrderLine(
                code=code,
                mat_code=mat_code,
                purchase_length_mm=purchase_length_mm,
                quantity=quantity,
                article_number=article_number(code, mat_code, purchase_length_mm),
                price_per_unit_sek=price,
                lead_time_days=MOCK_LEAD_TIME_DAYS,
                total_price_sek=round(price * quantity, 2),
            )
        )

    lines.sort(key=lambda line: (line.code, line.mat_code, line.purchase_length_mm))
    return lines


def build_summary(
    results: list[GroupCuttingResult], order_lines: list[PurchaseOrderLine]
) -> PurchaseOrderSummary:
    """Summera total spillprocent, total kostnad, totalt antal stänger m.m."""
    total_bars = sum(len(result.bars) for result in results)
    purchased_mm = sum(bar.purchase_length_mm for result in results for bar in result.bars)
    needed_mm = sum(
        cut.length_mm for result in results for bar in result.bars for cut in bar.cuts
    )
    splices = [splice for result in results for splice in result.splices]

    return PurchaseOrderSummary(
        total_bars=total_bars,
        total_needed_length_mm=round(needed_mm, 1),
        total_purchased_length_mm=round(purchased_mm, 1),
        total_waste_percent=(
            round((purchased_mm - needed_mm) / purchased_mm * 100, 2) if purchased_mm else 0.0
        ),
        total_cost_sek=round(sum(line.total_price_sek for line in order_lines), 2),
        spliced_piece_count=len(splices),
        total_joints=sum(splice.joint_count for splice in splices),
    )


def build_baseline(results: list[GroupCuttingResult], trade_lengths_mm: list[int]) -> Baseline:
    """Räkna fram den ooptimerade baslinjen: en handelslängd per kapbit (data/dataspec.md §7).

    Detta är rutinen optimeringen ersätter — varje bit köps i närmast längre handelslängd och
    resten blir spill. Skarvade bitar räknas som sina segment, dvs. samma fysiska behov som
    optimeringen fick, så jämförelsen är rättvis.
    """
    longest = trade_lengths_mm[-1]
    total_bars = 0
    purchased_mm = 0
    needed_mm = 0.0
    cost_sek = 0.0

    for result in results:
        for bar in result.bars:
            for cut in bar.cuts:
                length = next(
                    (t for t in trade_lengths_mm if cut.length_mm + KERF_MM <= t + 1e-9),
                    longest,
                )
                total_bars += 1
                purchased_mm += length
                needed_mm += cut.length_mm
                cost_sek += _price_per_unit_sek(result.mat_code, length)

    optimized_mm = sum(bar.purchase_length_mm for result in results for bar in result.bars)
    optimized_cost = sum(
        _price_per_unit_sek(result.mat_code, bar.purchase_length_mm)
        for result in results
        for bar in result.bars
    )

    return Baseline(
        total_bars=total_bars,
        total_purchased_length_mm=round(float(purchased_mm), 1),
        total_waste_percent=(
            round((purchased_mm - needed_mm) / purchased_mm * 100, 2) if purchased_mm else 0.0
        ),
        total_cost_sek=round(cost_sek, 2),
        saved_length_mm=round(float(purchased_mm - optimized_mm), 1),
        saved_cost_sek=round(cost_sek - optimized_cost, 2),
        saved_percent=(
            round((purchased_mm - optimized_mm) / purchased_mm * 100, 2) if purchased_mm else 0.0
        ),
    )

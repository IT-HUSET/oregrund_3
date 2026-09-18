"""Enhetstester för inkrement 3: FFD-kapoptimering med kerf och skarvning.

docs/plan.md #3, docs/adr.md ADR-2. Testerna kör mot syntetiska grupper där facit går att
räkna för hand — /api-nivån testas i test_purchase_order.py mot den riktiga datan.
"""

import pytest

from app.models import BomGroup, GroupedPiece
from app.services.cutting_optimizer import optimize_group

KERF = 3.0
TRADE_LENGTHS = list(range(1800, 5401, 300))


def _group(lengths: list[float], code: str = "45x182", mat_code: str = "C24") -> BomGroup:
    pieces = [GroupedPiece(oid=str(9000 + i), length_mm=l) for i, l in enumerate(lengths)]
    return BomGroup(
        code=code,
        mat_code=mat_code,
        piece_count=len(pieces),
        total_length_mm=sum(lengths),
        pieces=pieces,
        available_trade_lengths_mm=TRADE_LENGTHS,
    )


def _assert_balances(result) -> None:
    """docs/plan.md #3: materialet balanserar på varje stång."""
    for bar in result.bars:
        cuts_sum = sum(cut.length_mm for cut in bar.cuts)
        assert cuts_sum + bar.kerf_total_mm == pytest.approx(bar.used_length_mm)
        assert bar.used_length_mm + bar.waste_mm == pytest.approx(bar.purchase_length_mm)
        assert bar.used_length_mm <= bar.purchase_length_mm + 1e-9


def test_single_short_piece_uses_shortest_fitting_trade_length():
    result = optimize_group(_group([255.0]), KERF)

    assert len(result.bars) == 1
    assert result.bars[0].purchase_length_mm == 1800
    _assert_balances(result)


def test_kerf_is_charged_once_per_cut():
    """Konvention: ett kerf-avdrag per kapad bit (se moduldocstring i cutting_optimizer)."""
    result = optimize_group(_group([1000.0, 500.0, 250.0]), KERF)

    assert len(result.bars) == 1
    bar = result.bars[0]
    assert bar.kerf_total_mm == pytest.approx(3 * KERF)
    assert bar.used_length_mm == pytest.approx(1750.0 + 3 * KERF)
    _assert_balances(result)


def test_kerf_forces_an_extra_bar_when_it_just_does_not_fit():
    """2 x 900 mm ryms i 1800 mm rent, men inte med 2 x 3 mm kerf."""
    result = optimize_group(_group([900.0, 900.0]), KERF)

    assert sum(len(bar.cuts) for bar in result.bars) == 2
    for bar in result.bars:
        assert bar.used_length_mm <= bar.purchase_length_mm
    _assert_balances(result)


def test_ffd_packs_longest_first_into_one_bar():
    """1200 + 900 + 600 + 3 x kerf = 2709 -> ryms i 2700? Nej -> 3000 mm-stång."""
    result = optimize_group(_group([600.0, 1200.0, 900.0]), KERF)

    assert len(result.bars) == 1
    bar = result.bars[0]
    assert [cut.length_mm for cut in bar.cuts] == [1200.0, 900.0, 600.0]
    assert bar.purchase_length_mm == 3000
    _assert_balances(result)


def test_every_piece_is_cut_exactly_once():
    lengths = [2500.0, 1800.0, 47.0, 3300.0, 900.0, 1200.0, 255.0, 4000.0]
    result = optimize_group(_group(lengths), KERF)

    cut_lengths = sorted(cut.length_mm for bar in result.bars for cut in bar.cuts)
    assert cut_lengths == sorted(lengths)
    _assert_balances(result)


def test_waste_percent_is_consistent_with_bars():
    result = optimize_group(_group([2500.0, 1800.0, 900.0]), KERF)

    purchased = sum(bar.purchase_length_mm for bar in result.bars)
    needed = sum(cut.length_mm for bar in result.bars for cut in bar.cuts)
    assert result.waste_percent == pytest.approx(round((purchased - needed) / purchased * 100, 2))


# --- Skarvning (docs/prd.md §3.3, docs/adr.md ADR-2 tillägg) -----------------------------


def test_oversized_piece_is_spliced_across_several_bars():
    """9725 mm är längre än 5400 mm och kan inte köpas som en bit."""
    result = optimize_group(_group([9725.0]), KERF)

    assert len(result.splices) == 1
    splice = result.splices[0]
    assert splice.total_length_mm == 9725.0
    assert splice.segment_count == 2
    assert splice.joint_count == 1

    segments = [cut for bar in result.bars for cut in bar.cuts if cut.oid == splice.oid]
    assert len(segments) == 2
    assert all(cut.spliced for cut in segments)
    assert sorted(cut.segment_index for cut in segments) == [1, 2]
    assert all(cut.segment_count == 2 for cut in segments)
    _assert_balances(result)


def test_spliced_segments_sum_to_the_full_needed_length():
    """docs/api-contract.md: sum(cuts med detta oid) == splices[].total_length_mm."""
    result = optimize_group(_group([9725.0, 6000.0]), KERF)

    for splice in result.splices:
        covered = sum(
            cut.length_mm for bar in result.bars for cut in bar.cuts if cut.oid == splice.oid
        )
        assert covered == pytest.approx(splice.total_length_mm)


def test_piece_at_the_limit_is_not_spliced():
    """5397 mm ryms i 5400 mm med kerf — ska INTE flaggas som skarvad."""
    result = optimize_group(_group([5397.0]), KERF)

    assert result.splices == []
    assert all(not cut.spliced for bar in result.bars for cut in bar.cuts)


def test_normal_pieces_are_not_flagged_as_spliced():
    result = optimize_group(_group([1000.0, 2000.0]), KERF)

    assert result.splices == []
    for bar in result.bars:
        for cut in bar.cuts:
            assert cut.spliced is False
            assert cut.segment_index is None
            assert cut.segment_count is None


def test_very_long_piece_needs_more_than_two_segments():
    result = optimize_group(_group([13000.0]), KERF)

    splice = result.splices[0]
    assert splice.segment_count == 3
    assert splice.joint_count == 2
    assert sum(splice.purchase_lengths_mm) >= 13000


def test_group_without_trade_lengths_raises():
    group = _group([1000.0])
    group.available_trade_lengths_mm = []

    with pytest.raises(ValueError, match="handelslängder"):
        optimize_group(group, KERF)


# --- Gränsfall kring längsta handelslängden ----------------------------------------------
# En stång rymmer handelslängden MINUS ett kerf. Bitar i intervallet (5400-kerf, 5400] ser ut
# att rymmas i en 5400-stång men gör det inte när kerfen räknas med — de måste skarvas.


@pytest.mark.parametrize("length", [5397.5, 5398.0, 5399.0, 5400.0, 5401.0])
def test_pieces_just_over_capacity_are_spliced_not_overpacked(length):
    result = optimize_group(_group([length]), KERF)

    assert result.splices, f"{length} mm ryms inte i 5400 mm med kerf och måste skarvas"
    _assert_balances(result)


@pytest.mark.parametrize("length", [5396.0, 5397.0])
def test_pieces_at_or_below_capacity_are_not_spliced(length):
    result = optimize_group(_group([length]), KERF)

    assert result.splices == []
    assert len(result.bars) == 1
    assert result.bars[0].purchase_length_mm == 5400
    _assert_balances(result)


def test_no_bar_ever_has_negative_waste():
    """Negativt spill = biten får inte plats i stången den påstås vara skuren ur."""
    lengths = [5396.0, 5397.0, 5398.0, 5400.0, 5401.0, 9725.0, 47.0, 1797.0, 1798.0]
    result = optimize_group(_group(lengths), KERF)

    for bar in result.bars:
        assert bar.waste_mm >= 0, bar
        assert bar.used_length_mm <= bar.purchase_length_mm

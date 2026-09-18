"""Gruppera BOM-rader per (tvärsnitt, materialklass) och matcha mot handelslängder.

Inkrement 2, docs/plan.md rad 2.
"""

import csv
from pathlib import Path

from app.models import BomGroup, FramePieceOut, GroupedPiece

#: Kapoptimeringen (inkrement 3) gäller bara kapbart regelvirke. Undantagen nedan kommer ur
#: data/dataspec.md §5 och listas separat i stället för att packas mot handelslängder.
#: Grupperingen i /api/bom/groups visar däremot ALLA grupper — även de undantagna — så att
#: underlaget går att granska i sin helhet (docs/prd.md §3.2).
EXCLUDED_MAT_CODES = frozenset({"GL"})  # limträ: beställs i hel längd, kapas inte
EXCLUDED_USES = frozenset({"SHIMS"})  # kilar/distanser, inte regelvirke


def load_trade_lengths_mm(path: Path) -> list[int]:
    """Läs data/svensktra_standardlangder_mm.csv -> sorterad lista med handelslängder i mm.

    Hårdkoda ALDRIG handelslängderna i koden (AGENTS.md) — läs alltid från CSV:n.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"{path} innehåller inga handelslängder")

    column = "langd_mm"
    if column not in rows[0]:
        raise ValueError(f"{path} saknar kolumnen {column!r}, hittade {list(rows[0])}")

    return sorted(int(row[column]) for row in rows)


def exclusion_reason(piece: FramePieceOut) -> str | None:
    """Varför kapbiten inte kapoptimeras, eller None om den gör det (data/dataspec.md §5)."""
    if piece.mat_code in EXCLUDED_MAT_CODES:
        return "Limträ — beställs i hel längd, kapoptimeras inte"
    if piece.use in EXCLUDED_USES:
        return "Kilar/distanser (SHIMS) — kapoptimeras inte"
    return None


def is_optimizable(piece: FramePieceOut) -> bool:
    """True om kapbiten ska med i kapoptimeringen (data/dataspec.md §5)."""
    return exclusion_reason(piece) is None


def group_by_code_and_material(
    pieces: list[FramePieceOut], trade_lengths_mm: list[int]
) -> list[BomGroup]:
    """Gruppera per (code, mat_code) och bifoga tillgängliga handelslängder per grupp.

    Kontroll (docs/plan.md #2): gruppen 45x182/C24 har piece_count == 72 och listar
    handelslängderna 1800-5400 mm.

    Grupperna sorteras på fallande total längd — störst materialbehov först, vilket är det
    inköparen och kapoperatören bryr sig om (docs/prd.md §2).
    """
    grouped: dict[tuple[str, str], list[FramePieceOut]] = {}
    for piece in pieces:
        grouped.setdefault((piece.code, piece.mat_code), []).append(piece)

    groups = [
        BomGroup(
            code=code,
            mat_code=mat_code,
            piece_count=len(members),
            total_length_mm=round(sum(p.length_mm for p in members), 1),
            pieces=[GroupedPiece(oid=p.oid, length_mm=p.length_mm) for p in members],
            available_trade_lengths_mm=trade_lengths_mm,
            # Gruppen märks som undantagen bara om ALLA dess bitar är det — då är det en
            # egenskap hos gruppen och inte hos enstaka rader. Frontend slipper återskapa
            # regeln själv och kan inte hamna ur synk med backend.
            excluded_reason=next(
                (reason for p in members if (reason := exclusion_reason(p))), None
            )
            if all(exclusion_reason(p) for p in members)
            else None,
        )
        for (code, mat_code), members in grouped.items()
    ]

    groups.sort(key=lambda g: (-g.total_length_mm, g.code, g.mat_code))
    return groups

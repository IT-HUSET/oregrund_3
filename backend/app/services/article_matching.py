"""Gruppera BOM-rader per (tvärsnitt, materialklass) och matcha mot handelslängder.

Inkrement 2, docs/plan.md rad 2.
"""

import csv
from functools import lru_cache
from pathlib import Path

from app.config import TRADE_LENGTHS_CSV_PATH
from app.models import BomGroup, FramePieceOut, GroupedPiece


def load_trade_lengths_mm(path: Path) -> list[int]:
    """Läs data/svensktra_standardlangder_mm.csv -> sorterad lista med handelslängder i mm.

    Hårdkoda ALDRIG handelslängderna i koden (AGENTS.md) — läs alltid från CSV:n.
    """
    with path.open(newline="", encoding="utf-8") as f:
        lengths = [int(row["langd_mm"]) for row in csv.DictReader(f)]
    return sorted(lengths)


@lru_cache(maxsize=1)
def get_trade_lengths_mm() -> list[int]:
    """Cachad inläsning av handelslängderna -- läses en gång per processlivstid."""
    return load_trade_lengths_mm(TRADE_LENGTHS_CSV_PATH)


def group_by_code_and_material(
    pieces: list[FramePieceOut], trade_lengths_mm: list[int]
) -> list[BomGroup]:
    """Gruppera per (code, mat_code) och bifoga tillgängliga handelslängder per grupp.

    Kontroll (docs/plan.md #2): gruppen 45x182/C24 har piece_count == 72 och listar
    handelslängderna 1800-5400 mm.
    """
    groups: dict[tuple[str, str], list[FramePieceOut]] = {}
    for piece in pieces:
        groups.setdefault((piece.code, piece.mat_code), []).append(piece)

    return [
        BomGroup(
            code=code,
            mat_code=mat_code,
            piece_count=len(group_pieces),
            total_length_mm=sum(p.length_mm for p in group_pieces),
            pieces=[GroupedPiece(oid=p.oid, length_mm=p.length_mm) for p in group_pieces],
            available_trade_lengths_mm=trade_lengths_mm,
        )
        for (code, mat_code), group_pieces in sorted(groups.items())
    ]

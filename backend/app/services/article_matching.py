"""Gruppera BOM-rader per (tvärsnitt, materialklass) och matcha mot handelslängder.

Inkrement 2, docs/plan.md rad 2.
"""

from pathlib import Path

from app.models import BomGroup, FramePieceOut


def load_trade_lengths_mm(path: Path) -> list[int]:
    """Läs data/svensktra_standardlangder_mm.csv -> sorterad lista med handelslängder i mm.

    Hårdkoda ALDRIG handelslängderna i koden (AGENTS.md) — läs alltid från CSV:n.
    """
    raise NotImplementedError("Inkrement 2, se docs/plan.md rad 2")


def group_by_code_and_material(
    pieces: list[FramePieceOut], trade_lengths_mm: list[int]
) -> list[BomGroup]:
    """Gruppera per (code, mat_code) och bifoga tillgängliga handelslängder per grupp.

    Kontroll (docs/plan.md #2): gruppen 45x182/C24 har piece_count == 72 och listar
    handelslängderna 1800-5400 mm.
    """
    raise NotImplementedError("Inkrement 2, se docs/plan.md rad 2")

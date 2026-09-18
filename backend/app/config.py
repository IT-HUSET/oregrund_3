"""Delade konstanter och sökvägar. Se docs/adr.md och docs/api-contract.md."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

COMPONENTS_XML_PATH = DATA_DIR / "components.xml"
TRADE_LENGTHS_CSV_PATH = DATA_DIR / "svensktra_standardlangder_mm.csv"

# Sågklingans snittbredd, se docs/adr.md ADR-2. Dras av per snitt i kapoptimeringen.
KERF_MM = 3.0

# Backend öppnar aldrig .ifc-filen, se docs/adr.md ADR-3 — ingen IFC_PATH här med flit.

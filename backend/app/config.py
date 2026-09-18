"""Delade konstanter och sökvägar. Se docs/adr.md och docs/api-contract.md."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

COMPONENTS_XML_PATH = DATA_DIR / "components.xml"
TRADE_LENGTHS_CSV_PATH = DATA_DIR / "svensktra_standardlangder_mm.csv"

# Sågklingans snittbredd, se docs/adr.md ADR-2. Dras av per snitt i kapoptimeringen.
KERF_MM = 3.0

# Exakt kapoptimering (OR-Tools CP-SAT), se docs/adr.md ADR-2-tillägget. Används bara när
# algorithm=exact -- girig FFD (default) har ingen tidsgräns.
EXACT_SOLVER_TIME_BUDGET_S = 5.0
EXACT_SOLVER_NUM_WORKERS = 8

# Backend öppnar aldrig .ifc-filen, se docs/adr.md ADR-3 — ingen IFC_PATH här med flit.

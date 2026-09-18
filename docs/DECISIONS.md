# Decisions

<!-- Maintenance:
     - The `andthen:architecture` skill in `--mode trade-off` auto-registers
       ADRs (appends to Current ADRs; moves prior rows to Superseded on
       supersession). Idempotent on ADR ID.
     - "Still Current" captures load-bearing choices that don't warrant a full
       ADR. Promote via `--mode trade-off` if the choice becomes contested.
     - Status enum (Current ADRs): Proposed | Accepted | Deprecated.
       Superseded decisions move to the dedicated table; Rejected decisions
       stay only in the ADR file itself (not indexed). -->

## Current ADRs

<!-- This project keeps its ADRs inline in a single docs/adr.md rather than one file per
     decision under docs/adrs/ — a deliberate deviation from the default Project Document Index
     layout, kept as-is for this 4-hour-demo project. Full decision text, rationale, and cost
     ("Vad det kostar") live in docs/adr.md; this table is only an index. -->

| ID | Title | Status | Scope |
|-----|-------|--------|-------|
| ADR-1 | Separat backend (Python/FastAPI) för affärslogik, för parallellt arbete | Accepted | `docs/adr.md` |
| ADR-2 | Girig First-Fit-Decreasing istället för exakt ILP-lösare för kapoptimeringen | Accepted | `docs/adr.md` |
| ADR-3 | Etablerat open source-bibliotek (web-ifc / @thatopen/components) för IFC-rendering | Accepted | `docs/adr.md` |

## Superseded

<!-- Move prior rows here when a new ADR supersedes them. Never delete –
     the lineage is load-bearing context for agents reading the codebase. -->

_Inga hittills._

## Still Current

<!-- Load-bearing decisions that don't warrant a full ADR. One bullet each.
     Format: **<Topic>**: <decision + brief rationale>. -->

- **Scope**: 4-timmars tidsbox, demo kl. 18:00 samma dag — se `docs/prd.md` §0/§6.
- **Prioritering vid tidsbrist**: 3D-spårbarheten skärs aldrig först — kapoptimeringens
  sofistikering skärs istället (`docs/prd.md` §6, `docs/adr.md` ADR-3).

## Pending

<!-- Decisions under discussion, awaiting acceptance. Typically populated by
     the `andthen:architecture` skill in `--mode trade-off` when a
     recommendation hasn't yet been accepted as an ADR. -->

_Inga hittills._

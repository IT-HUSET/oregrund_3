# Product

## Vision
4-timmars demoprototyp åt Lindbäcks Bygg: automatisera vägen från ett verkligt
konstruktionsunderlag (`components.xml`, export ur Vertex BD) till ett granskningsbart
inköpsunderlag och spillrapport — matcha materialbehov mot handelslängder, kör kapoptimering
(1D cutting stock) och gör resultatet spårbart mot 3D-modellen (`772_H811_new.ifc`). Se
`docs/prd.md` för fullständiga krav.

## Target Users
- **Konstruktör**: verifiera att materiallistan stämmer mot 3D-modellen — lita på underlaget
  utan manuell dubbelkontroll.
- **Inköpare**: få ett färdigt inköpsunderlag mot handelslängder — rätt volymer, snabbare
  orderläggning.
- **Kapoperatör**: få en exakt, spilloptimerad kaplista — mindre spill, mindre tid vid sågen.

## Value Propositions
- **Konstruktör**: 3D-spårbarhet (klick i tabell → highlight i IFC-modell via OID↔Tag) ersätter
  manuell dubbelkontroll.
- **Inköpare**: automatisk artikel-/handelslängdsmatchning mot riktig Svenskt Trä-data eliminerar
  manuell mängdning.
- **Kapoperatör**: girig FFD-kapoptimering (inkl. skarvning av överlånga behov) minimerar spill
  utan en tung exakt lösare.

## Key Capabilities
| Capability | Description | Status |
|------------|--------------|--------|
| Inläsning av konstruktionsunderlag | Parsa `components.xml` → strukturerad materialbehovslista | In Progress (boilerplate/fixture-läge, se `docs/plan.md` #1) |
| Artikel-/handelslängdsmatchning | Gruppera behov och matcha mot `data/svensktra_standardlangder_mm.csv` | Planned (`docs/plan.md` #2) |
| Kapoptimering + spillrapport | Girig FFD, kerf-hänsyn, skarvning av behov > 5400 mm | Planned (`docs/plan.md` #3) |
| Visuell 3D-spårbarhet | Klick i inköpsunderlag highlightar element i IFC-vyn | Planned (`docs/plan.md` #4) |
| Granskningsbart inköpsunderlag | Exporterbar tabell: längder, antal, kostnad, spillprocent | Planned (`docs/plan.md` #3) |

## Non-Goals
Se `docs/prd.md` §4 för den fullständiga, auktoritativa listan. Sammanfattat:
- Bildbaserad AI-tolkning av ritningar/CAD (indata är redan strukturerad).
- Automatisk bindande orderläggning hos leverantör (inget API/EDI-anrop).
- Redigering av `components.xml`/`.ifc` (läses, skrivs aldrig).
- Riktiga priser/artikelnummer/leveranstider (mockas; handelslängderna är riktig data).
- Icke-träbaserat material, multi-projekt/multi-fil-stöd.
- Strukturell validering av skarvplacering (skarvade rader flaggas för manuell granskning).

## Success Metrics
- Demo kl. 18:00 visar hela kedjan end-to-end: inläsning → matchning → kapoptimering →
  3D-spårbarhet → inköpsunderlag (`docs/prd.md` §5).
- Varje inkrement i `docs/plan.md` klarar sitt automattest **och** sitt manuella klicksteg.

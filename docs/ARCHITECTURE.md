# Architecture

## System Overview
Separat Python/FastAPI-backend (all affärslogik: XML-parsning, artikelmatchning, kapoptimering,
inköpsunderlag) exponerad som ett litet JSON-API, konsumerad av en React/TypeScript-frontend som
äger UI och 3D-rendering (`web-ifc` + `three.js`/`@thatopen/components`). Backend öppnar aldrig
IFC-filen; highlight sker klientsidan via en OID↔`Tag`-uppslagning. Se `docs/adr.md` för fulla
beslutstexter (ADR-1/2/3) och skiss.

## Key Components
| Component | Responsibility | Key Files/Dirs |
|-----------|-----------------|-----------------|
| Backend API | FastAPI-app, routrar, CORS | `backend/app/main.py`, `backend/app/routers/` |
| XML-parser | `components.xml` → `FramePieceOut` | `backend/app/services/xml_parser.py` |
| Artikelmatchning | Gruppering + handelslängdsmatchning mot `data/svensktra_standardlangder_mm.csv` | `backend/app/services/article_matching.py` |
| Kapoptimering | Girig FFD-algoritm, kerf, skarvning (ADR-2) | `backend/app/services/cutting_optimizer.py` |
| API-scheman | Pydantic-modeller för BOM-/kaplista-/inköpsradsobjekt | `backend/app/models.py` |
| Frontend UI | Tabellvy: BOM / kaplista / inköpsunderlag | `frontend/src/` |
| 3D-viewer | Laddar `772_H811_new.ifc`, bygger `expressID ↔ Tag`-karta, highlight | `frontend/src/` (web-ifc/@thatopen/components, ADR-3) |

## Data Flow
1. Backend läser `components.xml` och `data/svensktra_standardlangder_mm.csv` vid start.
2. `GET /api/bom` — parsad, grupperad materialbehovslista.
3. `GET /api/purchase-order` — kaplista, inköpsunderlag, spillrapport (via FFD-optimering).
4. Frontend hämtar båda endpoints, renderar tabeller och laddar IFC-modellen separat i klienten.
5. Klick på en rad i frontend slår upp radens `oid` mot IFC-modellens `Tag`-fält och highlightar
   motsvarande element — helt klientsidan, ingen ytterligare backend-anrop.

## Integration Points
| Service | Purpose | Config Location |
|---------|---------|-------------------|
| `components.xml` | Konstruktionsunderlag (Vertex BD-export), läses av backend | `backend/app/config.py` |
| `data/svensktra_standardlangder_mm.csv` | Handelslängder, läses av backend | `backend/app/config.py` |
| `772_H811_new.ifc` | 3D-modell, läses och renderas endast av frontend (ADR-3) | `frontend/` |

## Key Constraints
- Backend äger all affärslogik; frontend äger UI + 3D — se ADR-1 (`docs/adr.md`).
- Kapoptimering är girig FFD, inte exakt ILP — se ADR-2. Ändra inte utan att uppdatera ADR-2 först.
- Backend öppnar/parsar aldrig `.ifc`-filen — det är frontends jobb (ADR-3).
- `components.xml` och `772_H811_new.ifc` läses, skrivs aldrig.
- Hårdkoda inte handelslängder — läs alltid `data/svensktra_standardlangder_mm.csv`.

# AGENTS.md

## Vad det här är

4-timmars demoprototyp åt Lindbäcks Bygg: läs in ett verkligt konstruktionsunderlag
(`components.xml`, export ur Vertex BD), matcha materialbehovet mot handelslängder, kör
kapoptimering (1D cutting stock) och visa resultatet spårbart mot 3D-modellen
(`772_H811_new.ifc`). Slutprodukt: ett granskningsbart inköpsunderlag + spillrapport.

Arkitektur: separat Python/FastAPI-backend (all affärslogik: parsning, matchning, optimering)
+ React/TypeScript-frontend (UI + 3D-viewer). Se `docs/adr.md` för varför.

## Läs först

- `docs/prd.md` — krav, roller, vad som INTE byggs
- `docs/adr.md` — arkitekturskiss och tre beslut (backend-split, optimeringsalgoritm, 3D-bibliotek)
- `docs/plan.md` — de fyra inkrementen, i visningsordning, med kontroll per rad

## Projektdokumentindex

<!-- Talar om för AndThen-skills var projektet har sina dokument. Rader borttagna som inte
     används. Sökvägar relativa till repo-roten. ADR:erna ligger inline i docs/adr.md, inte en
     fil per beslut under docs/adrs/ — en medveten avvikelse från AndThens defaultlayout för det
     här 4-timmarsprojektet. -->

| Dokumenttyp | Plats | Notering |
|---|---|---|
| Product | `docs/PRODUCT.md` | Produktvision, målgrupper, kapabiliteter |
| PRD | `docs/prd.md` | Krav, roller, vad som INTE byggs |
| Plan | `docs/plan.md` | De fyra inkrementen, kontroll per rad |
| API-kontrakt | `docs/api-contract.md` | Fälten i backend-API:ets JSON-svar |
| Decisions | `docs/DECISIONS.md` | ADR-index — pekar in i `docs/adr.md` |
| ADR:er (fulltext) | `docs/adr.md` | ADR-1/2/3, inline (avviker från `docs/adrs/`) |
| Architecture | `docs/ARCHITECTURE.md` | Systemöversikt, komponenter, dataflöde |
| Stack | `docs/STACK.md` | Teknikstack med versioner |
| Key Dev Commands | `docs/KEY_DEVELOPMENT_COMMANDS.md` | Kör/test/build-kommandon |
| Learnings | `docs/LEARNINGS.md` | Fallgropar/kunskapsindex |
| Guidelines | `docs/guidelines/` | Utvecklingsriktlinjer |
| Issue Tracker | `docs/ISSUE-TRACKER.md` | Backend: GitHub |
| Agent Temp | `.agent_temp/` | Temporär agent-workspace (gitignored) |

## Kör

Backend (`backend/`):
```
uvicorn app.main:app --reload --port 8000
```

Frontend (`frontend/`):
```
npm run dev          # http://localhost:5173, proxyar /api mot backend
```

Om `backend/`/`frontend/` inte finns än: det är dit koden ska, enligt skissen i `docs/adr.md`.
Skapa inte en annan mappstruktur utan att uppdatera `adr.md` först.

## Testa

- Backend: `pytest` i `backend/`
- Kontroll per inkrement: se kolumnen "Kontroll (test | klick)" i `docs/plan.md` — varje rad har
  både ett automattest och ett manuellt klicksteg. Ett inkrement räknas inte klart förrän båda är
  gjorda.

**Läs alltid** `docs/guidelines/CRITICAL-RULES-AND-GUARDRAILS.md` — generella arbetsregler
(scope-disciplin, verifiering, git) som gäller utöver punkterna nedan.

## Gör inte

- Bygg ingen bild-/CAD-tolknings-AI — indata är redan strukturerad (`components.xml`), se
  `docs/prd.md` §0 och §4.
- Skicka ingen bindande order till leverantör (inget API/EDI-anrop).
- Redigera aldrig `components.xml` eller `772_H811_new.ifc` — de läses, aldrig skrivs.
- Låt inte backend öppna eller parsa `.ifc`-filen — det är frontends jobb (`docs/adr.md` ADR-3).
- Hårdkoda inte handelslängder i koden — läs `data/svensktra_standardlangder_mm.csv`.
- Byt inte kapoptimeringen mot en exakt ILP-lösare "för att det är bättre" — beslutet (girig
  FFD) står i `docs/adr.md` ADR-2, ändra där först om det ska ändras.
- Skär inte bort 3D-spårbarheten vid tidsbrist — skär hellre i optimeringens sofistikering
  (`docs/adr.md` ADR-3, `docs/prd.md` §6).
- Lägg inte till nya krav eller scope utanför `docs/prd.md` §3 utan att uppdatera PRD:n först.

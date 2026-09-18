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

## Kör

Backend (`backend/`):
```
uvicorn app.main:app --reload --port 8000
```

Frontend (`frontend/`):
```
npm run dev          # http://localhost:5173, proxyar /api mot backend
```

Frontend kräver **Node 20.19+** (Vite 8); på Node 18 kraschar bygget. Se `frontend/README.md`.

Om `backend/`/`frontend/` inte finns än: det är dit koden ska, enligt skissen i `docs/adr.md`.
Skapa inte en annan mappstruktur utan att uppdatera `adr.md` först.

## Testa

- Backend: `pytest` i `backend/`
- Frontend: `npm run build` (typkontroll), `npm run lint`, och `npm run verify:ifc` som
  kontrollerar OID↔Tag-kopplingen mot den riktiga IFC-filen
- Kontroll per inkrement: se kolumnen "Kontroll (test | klick)" i `docs/plan.md` — varje rad har
  både ett automattest och ett manuellt klicksteg. Ett inkrement räknas inte klart förrän båda är
  gjorda.

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

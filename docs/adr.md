# Arkitektur och beslut — AI-baserat Inköps- och Spilloptimeringsflöde

Prototyp, tidsbox 4h. Se `docs/prd.md` för krav/scope. Besluten nedan gäller för hela
byggsessionen — avvik inte från dem utan att uppdatera den här filen.

## Skiss

```
┌───────────────────────┐      HTTP/JSON API      ┌──────────────────────────────────┐
│   Frontend (SPA)        │ ─────────────────────▶ │   Backend (Python API)              │
│   React + TS + Vite     │ ◀───────────────────── │   FastAPI + Pydantic                │
│                          │      GET /api/bom      │                                      │
│  - Ladda & rendera         │  GET /api/purchase-order│  Läser vid start: components.xml,     │
│    772_H811_new.ifc        │                         │  data/svensktra_*.csv                 │
│    (web-ifc + three.js)    │                         │                                       │
│  - Tabellvy: BOM /          │                        │  - XML-parser: FRAMEPIECE → behovslista│
│    kaplista / inköps-       │                        │  - Artikel-/handelslängdsmatchning     │
│    underlag                 │                        │  - Kapoptimering (FFD-heuristik+kerf)  │
│  - Highlight i 3D: matchar  │                        │  - Spillrapport + inköpsunderlag       │
│    OID från API mot IFC      │                       │  - All affärslogik & tillstånd bor här │
│    Tag-fält (klientsidan,    │                       │    (inte i frontend)                    │
│    IFC-filen rör backend     │                       │                                          │
│    aldrig)                   │                       │                                          │
└───────────────────────┘                              └──────────────────────────────────┘
```

Backend äger all affärslogik (parsning av `components.xml`, artikelmatchning, kapoptimering,
inköpsunderlag) och exponerar den som ett JSON-API. Frontend äger UI och 3D-rendering av
`772_H811_new.ifc` (måste köras i webbläsaren, WebGL) och gör highlight genom att slå upp
OID-värden (som följer med i API-svaret) mot IFC-filens `Tag`-fält lokalt i klienten. Backend
öppnar aldrig den 18 MB stora IFC-filen.

## Beslut

### ADR-1: Separat backend för affärslogik, och 3–4 personer måste kunna jobba parallellt

**Läget:** Vi är 3–4 personer på 4 timmar. Om all logik (XML-parsning, artikelmatchning,
kapoptimering) ligger inbakad i samma SPA som 3D-vyn blockerar frontend- och backend-arbete
varandra, och det finns inget att jobba mot förrän hela kedjan är klar. Vi behöver kunna dela upp
arbetet från minut ett.

**Vad vi valde:** Separat backend i Python (FastAPI, med Pydantic-modeller för BOM-/kaplista-/
inköpsradsobjekten) som äger all affärslogik och exponerar den som ett litet JSON-API
(`GET /api/bom`, `GET /api/purchase-order`, se skiss ovan) — teamet är starkare i Python än i
Node, och det väger tyngre än att dela språk med frontend. Frontend (Vite + React + TS) är en ren
klient mot det API:et plus 3D-vyn. API-kontraktet (fälten i respons-JSON, inkl. `oid` per rad)
spikas skriftligt först (i denna fil eller en delad `openapi.json`/exempel-JSON), sen kan två
personer bygga backend-logik (parsning+matchning, optimering+spillrapport) och två personer bygga
frontend (tabell/export, 3D-viewer+highlight) parallellt mot en mockad/statisk JSON-fixture tills
det riktiga API:et är klart.

**Vad det kostar:** Två språk i stacken (Python backend, TS frontend) istället för ett — inga
delade typer automatiskt, så kontraktet måste hållas synkat för hand eller via FastAPIs
auto-genererade OpenAPI-schema. Ändras ett fält i backend-svaret utan att frontend uppdateras blir
det trasigt tyst, inte ett kompileringsfel. En extra process att köra jämfört med en ren SPA, men
det vinns tillbaka direkt genom att arbetet går att parallellisera och köra i språket teamet är
snabbast i.

### ADR-2: Girig heuristik (First-Fit-Decreasing) istället för exakt ILP-lösare för kapoptimeringen

**Läget:** 1D cutting-stock-problemet är NP-svårt i sin exakta form. En exakt lösare
(t.ex. ett ILP via OR-Tools) ger optimalt resultat men kräver antingen en dedikerad solver-
integration eller en tung WASM-bundling, vilket äter av de redan knappa 4 timmarna och gör
resultatet svårare att felsöka/förklara live.

**Vad vi valde:** Implementera kapoptimeringen som en girig First-Fit-Decreasing-algoritm i
backend (Python, enligt ADR-1): sortera kaplängder fallande per (tvärsnitt, materialklass),
packa mot tillgängliga handelslängder (`data/svensktra_standardlangder_mm.csv`) med kerf-avdrag
per snitt, exponera resultatet via `GET /api/purchase-order`.

**Vad det kostar:** Resultatet är inte garanterat globalt optimalt — några extra procent spill
jämfört med en exakt lösare är förväntat och accepterat för en demo. Vinsten är att algoritmen är
liten, deterministisk, snabb att köra live och enkel att förklara för publiken på scen.

### ADR-3: Etablerat open source-bibliotek för IFC-rendering (web-ifc / @thatopen/components) istället för egen parser

**Läget:** Kravet på skarp 3D-spårbarhet (klick i tabell → highlight i 3D, via OID↔Tag-kopplingen,
se `prd.md` §0/§3.4) kräver att `772_H811_new.ifc` faktiskt renderas och att enskilda element kan
väljas och lysas upp programmatiskt. Att skriva en egen IFC-parser och 3D-renderare från grunden
är inte rimligt på 4h.

**Vad vi valde:** Använd `web-ifc` (WASM IFC-parser) tillsammans med `@thatopen/components` /
`three.js` för rendering, val och highlight av element — helt i frontend, enligt ADR-1. Backend
skickar bara `oid` per rad i sina API-svar (den behöver aldrig öppna IFC-filen); frontend bygger
själv en mappningstabell IFC `expressID` → `Tag` vid inläsning av modellen och slår upp
`Tag === oid` när en rad klickas.

**Vad det kostar:** Ett beroende av ett tredjepartsbiblioteks API-yta och dokumentation som vi
inte kontrollerar tidsåtgången för att lära oss under demodagen — detta är enligt `prd.md` §6/§7
den enskilt största tidsrisken, och skärs inte vid resursbrist (annat skärs istället). Highlight
begränsas till element med verifierad OID↔Tag-koppling (`FRAMEPIECE`/`IFCBEAM`), inte hela
modellen. Den som bygger 3D-vyn kan jobba isolerat mot en handfull kända OID:er tills backend-
API:et är klart.

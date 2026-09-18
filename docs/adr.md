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

### ADR-2: Girig heuristik (First-Fit-Decreasing) som standard, exakt lösare valbar av användaren

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

**Tillägg (skarvning):** Efter att fyndet i `prd.md` §0 gjordes — 43 av 299 unika kaplängder i
`components.xml` överstiger 5400 mm (längsta handelslängden) — utökas algoritmen till att
täcka ett behov med *flera* inköpta längder (skarv) när ingen enskild handelslängd räcker.
Detta ändrar inte beslutet ovan (fortfarande girig FFD, inte ILP): för behov > 5400 mm summeras
tillgängliga handelslängder girigt (störst först, minus kerf per snitt/skarv) tills täckning
uppnås, och raden flaggas `spliced=true` i API-svaret. Algoritmen optimerar bara materialtäckning
och spill — den validerar inte skarvens strukturella placering, se `prd.md` §3.3/§4.

**Tillägg (valbar exakt lösare, efterarbete 2026-09-18):** Frågan kom upp igen efter demot: hur
mycket spill faktiskt kostar det att välja girig FFD istället för en exakt lösare? Mättes med ett
spike (branch `spike/exact-cutting-optimizer`, `backend/spikes/exact_cutting_spike.py`) — OR-Tools
CP-SAT, formulerat som bin packing med variabel stånglängd (minimera total inköpt längd), kört mot
riktiga grupper ur `components.xml`:

| Grupp | Bitar | Girig FFD | Exakt (tidsgräns) | Besparing |
|---|---|---|---|---|
| `45x195/C24` | 13 (alla 2280 mm) | 5,00 % spill | 5,00 % spill, bevisat optimalt på 0,0 s | 0 mm — FFD redan optimal vid enhetliga längder |
| `45x182/C24` | 68 | 5,75 % spill | 4,25 % @ 5 s / 3,73 % @ 60 s, **ej bevisat optimalt** | 1,6–2,1 % |
| `45x220/C24` (störst) | 115 | 7,37 % spill | 6,00 % @ 15 s, **ej bevisat optimalt** | 1,46 % |

Slutsats: vinsten är verklig men liten (0–2 procentenheter mindre spill) på grupper med varierande
kaplängder, och obefintlig på grupper med enhetliga längder. CP-SAT bevisar inte global
optimalitet för de större grupperna inom en demo-vänlig tidsgräns — bara "bästa hittade hittills".

**Nytt beslut:** Girig FFD förblir standard och oförändrad (ovanstående beslut står kvar). En
exakt lösare (OR-Tools CP-SAT) läggs till som ett explicit, användarvalt alternativ — inte som ny
standard: `GET /api/purchase-order` får en valfri query-parameter `algorithm`
(`greedy` default | `exact`, se `docs/api-contract.md`). Vid `exact` körs CP-SAT per grupp med en
tidsgräns (konfigurerbar konstant i `backend/app/config.py`, aldrig hårdkodad inline); varje
`GroupCuttingResult` får ett `optimal`-fält så att UI kan visa om lösningen är bevisat bäst eller
bara "bästa hittade inom tidsgränsen".

**Vad det nya alternativet kostar:** Nytt beroende (`ortools`) i backend, bara relevant när
`exact` väljs. Svarstiden för `algorithm=exact` blir sekunder istället för millisekunder och
skalar med gruppstorlek — värsta fallet (alla 24 grupper, full tidsgräns var) kan bli
minuter, inte lämpligt som standard vid sidladdning. Detta är därför en explicit,
användarinitierad omräkning i UI:t (t.ex. en "Kör exakt optimering"-knapp med tydlig
väntetid/spinner), inte något som körs automatiskt. Svårare att förklara/felsöka live på scen än
girig FFD — därför förblir girig standardvalet.

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

# Inkrementell plan — AI-baserat Inköps- och Spilloptimeringsflöde

Fyra inkrement, i den ordning de visas i demot. Varje inkrement är en fungerande vertikal skiva
(backend + frontend, ev. 3D) som går att visa för sig — inte ett lager i arkitekturen. Se
`docs/prd.md` för krav/scope och `docs/adr.md` för arkitektur.

| # | Inkrement | Demovärde | Scenario | Kontroll (test \| klick) | Status |
|---|---|---|---|---|---|
| 1 | **Skelett — läs in och visa materialbehov** | Bevisar att hela kedjan (Python-backend ↔ React-frontend) fungerar end-to-end, och att manuell mängdning är borta: 731 verkliga rader dyker upp automatiskt, inte hårdkodat. | Backend parsar `components.xml` vid start (alla `FRAMEPIECE`) och svarar på `GET /api/bom`. Frontend hämtar och renderar en tabell: tvärsnitt, längd, klass, modul, funktion. | **Test:** `GET /api/bom` → 200, `len(items) == 731`. **Klick:** öppna appen, tabellen är fylld; filtrera på tvärsnitt `45x182` → 72 träffar. | Klar |
| 2 | **Artikelmatchning mot handelslängder** | Visar att systemet vet vilka handelslängder som faktiskt går att köpa (Svenskt Trä-standard) och grupperar rätt behov — grunden för optimeringen. | Backend grupperar BOM-raderna per (tvärsnitt, materialklass) och matchar mot `data/svensktra_standardlangder_mm.csv`. Frontend visar en grupperad vy: grupp, antal behövda bitar, tillgängliga handelslängder. | **Test:** gruppen `45x182/C24` innehåller exakt 72 rader och listar handelslängderna 1800–5400 mm. **Klick:** expandera gruppen `45x182 C24` i UI, se handelslängderna listade. | Klar |
| 3 | **Kapoptimering, spillrapport & inköpsunderlag** | Kärnvärdet i caset: konkret materialbesparing i procent och ett färdigt, granskningsbart inköpsunderlag att exportera. | Backend kör FFD-algoritmen per grupp (kerf inräknat), returnerar kaplista + antal inköpslängder + spillprocent via `GET /api/purchase-order`. Frontend visar kaplista, total spillprocent, exportknapp (CSV). | **Test:** för en känd grupp, summan av kaplängder + kerf + spill == summan av inköpta längder (materialet balanserar); spillprocent inom rimligt intervall. **Klick:** klicka "Exportera inköpsunderlag", öppna CSV:n, jämför mot UI. | Klar |
| 4 | **3D-spårbarhet** | Bygger förtroende — varje rad i inköpsunderlaget kan verifieras visuellt mot den riktiga 3D-modellen, inte bara siffror i en tabell. | Frontend laddar `772_H811_new.ifc` (web-ifc + three.js) och bygger en `expressID ↔ Tag`-karta över `IFCBEAM` + `IFCCOLUMN` (100 % täckning, `prd.md` §0). Klick på en rad i inköpsunderlaget slår upp radens `oid` mot `Tag` och highlightar elementet i 3D-vyn; klick på ett element i 3D-vyn visar samma bits uppgifter ur materiallistan (`prd.md` §3.4). | **Test:** givet känt OID `589830`, mappningen hittar rätt `expressID` i den laddade IFC-modellen. **Klick:** klicka raden för OID 589830, se balken lysa upp i 3D-vyn; klicka sedan ett annat element i 3D-vyn och se dess rad. | Klar |

## Ordningsprincip

Ordningen följer PRD:ns demoflöde (`prd.md` §5) och är samtidigt beroendekedjan: 2 kräver BOM
från 1, 3 kräver grupperingen från 2, 4 kräver `oid`-fältet som redan finns i svaret från 3 (och
alla tidigare). Varje inkrement kan alltså visas för sig så fort det är klart, utan att vänta på
nästa — om tiden tar slut efter inkrement 3 finns fortfarande ett komplett, demobart flöde utan
3D-spårbarhet (se `adr.md` ADR-3 och `prd.md` §6 för fallback-ordning).

## Tillägg efter demot: valbar exakt optimeringsalgoritm

`prd.md` §3.6 / `adr.md` ADR-2-tillägget (2026-09-18): utöver girig FFD i inkrement 3 kan
användaren välja en exakt lösare (OR-Tools CP-SAT) via `algorithm=exact` på
`GET /api/purchase-order`. Bygger ovanpå inkrement 3 (samma grupper, samma kontrakt plus nya
fält), rör inte inkrement 1/2/4. Status: **klart**. Backend i `app/services/cutting_optimizer.py`
`_solve_exact`; frontend i `PurchaseOrderView` — knappen "Kör exakt optimering" med
förloppsräknare, växling mellan de två resultaten när båda finns, jämförelserad (spill, antal
stänger, kostnad) och per grupp "bevisat optimal" / "bästa hittade" med lösningstid.
Ursprungligt spike med de uppmätta spilltalen finns kvar på branchen
`spike/exact-cutting-optimizer` (`backend/spikes/exact_cutting_spike.py`) som referens. Girig FFD
förblir standardläget; inkrement 3:s befintliga kontrollrad ovan gäller oförändrad för det.

**Kontroll (nytt):** `GET /api/purchase-order?algorithm=exact` → 200, `algorithm == "exact"` i
svaret; varje grupp balanserar materialet precis som för `greedy` (samma invariant som
inkrement 3:s kontrollrad); `groups[].optimal` är `false` för grupper där lösaren inte hann
bevisa optimalitet inom tidsgränsen (t.ex. de större grupperna, se ADR-2-tillägget).
**Klick:** öppna Inköpsunderlag, tryck "Kör exakt optimering", vänta ut räknaren, se
jämförelseraden och växla tillbaka till girig FFD.

**Två observationer från körningarna, att ha med sig på scen:**
- Resultatet är **inte reproducerbart mellan körningar**. Två identiska anrop gav 3,74 % spill /
  523 stänger respektive 5,09 % spill / 524 stänger. CP-SAT körs med wall-clock-tidsgräns
  (`EXACT_SOLVER_TIME_BUDGET_S`) och 8 trådar, så vilken lösning som hinner hittas varierar.
  Citera inte en exakt siffra i förväg — läs av den som står på skärmen.
- Totalen blir bättre, men **enskilda grupper kan bli sämre än girig FFD**: `45x220 C24` gick från
  6,38 % (girig) till 12,05 % (exakt) i samma körning där totalen förbättrades från 6,11 % till
  5,09 %. Lösarens målfunktion är inte spillprocent per grupp.

# Inkrementell plan — AI-baserat Inköps- och Spilloptimeringsflöde

Fyra inkrement, i den ordning de visas i demot. Varje inkrement är en fungerande vertikal skiva
(backend + frontend, ev. 3D) som går att visa för sig — inte ett lager i arkitekturen. Se
`docs/prd.md` för krav/scope och `docs/adr.md` för arkitektur.

| # | Inkrement | Demovärde | Scenario | Kontroll (test \| klick) | Status |
|---|---|---|---|---|---|
| 1 | **Skelett — läs in och visa materialbehov** | Bevisar att hela kedjan (Python-backend ↔ React-frontend) fungerar end-to-end, och att manuell mängdning är borta: 731 verkliga rader dyker upp automatiskt, inte hårdkodat. | Backend parsar `components.xml` vid start (alla `FRAMEPIECE`) och svarar på `GET /api/bom`. Frontend hämtar och renderar en tabell: tvärsnitt, längd, klass, modul, funktion. | **Test:** `GET /api/bom` → 200, `len(items) == 731`. **Klick:** öppna appen, tabellen är fylld; filtrera på tvärsnitt `45x182` → 72 träffar. | Påbörjad — backend klart, frontend kvar |
| 2 | **Artikelmatchning mot handelslängder** | Visar att systemet vet vilka handelslängder som faktiskt går att köpa (Svenskt Trä-standard) och grupperar rätt behov — grunden för optimeringen. | Backend grupperar BOM-raderna per (tvärsnitt, materialklass) och matchar mot `data/svensktra_standardlangder_mm.csv`. Frontend visar en grupperad vy: grupp, antal behövda bitar, tillgängliga handelslängder. | **Test:** gruppen `45x182/C24` innehåller exakt 72 rader och listar handelslängderna 1800–5400 mm. **Klick:** expandera gruppen `45x182 C24` i UI, se handelslängderna listade. | Påbörjad — backend klart, frontend kvar |
| 3 | **Kapoptimering, spillrapport & inköpsunderlag** | Kärnvärdet i caset: konkret materialbesparing i procent och ett färdigt, granskningsbart inköpsunderlag att exportera. | Backend kör FFD-algoritmen per grupp (kerf inräknat), returnerar kaplista + antal inköpslängder + spillprocent via `GET /api/purchase-order`. Frontend visar kaplista, total spillprocent, exportknapp (CSV). | **Test:** för en känd grupp, summan av kaplängder + kerf + spill == summan av inköpta längder (materialet balanserar); spillprocent inom rimligt intervall. **Klick:** klicka "Exportera inköpsunderlag", öppna CSV:n, jämför mot UI. | Påbörjad — backend klart, frontend kvar |
| 4 | **3D-spårbarhet** | Bygger förtroende — varje rad i inköpsunderlaget kan verifieras visuellt mot den riktiga 3D-modellen, inte bara siffror i en tabell. | Frontend laddar `772_H811_new.ifc` (web-ifc + three.js) och bygger en `expressID ↔ Tag`-karta. Klick på en rad i inköpsunderlaget slår upp raspektive `oid` mot `Tag` och highlightar elementet i 3D-vyn. | **Test:** givet känt OID `589830`, mappningen hittar rätt `expressID` i den laddade IFC-modellen. **Klick:** klicka raden för OID 589830, se balken "FD5 Opening header beam" lysa upp i 3D-vyn. | Ej påbörjad |

## Ordningsprincip

Ordningen följer PRD:ns demoflöde (`prd.md` §5) och är samtidigt beroendekedjan: 2 kräver BOM
från 1, 3 kräver grupperingen från 2, 4 kräver `oid`-fältet som redan finns i svaret från 3 (och
alla tidigare). Varje inkrement kan alltså visas för sig så fort det är klart, utan att vänta på
nästa — om tiden tar slut efter inkrement 3 finns fortfarande ett komplett, demobart flöde utan
3D-spårbarhet (se `adr.md` ADR-3 och `prd.md` §6 för fallback-ordning).

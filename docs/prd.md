# Product Requirement Document (PRD): AI-baserat Inköps- och Spilloptimeringsflöde
### — 4-timmars demoversion

**Projekt:** Från konstruktionsunderlag till kaplista och inköpsorder
**Kund / Kontext:** Lindbäcks Bygg
**Dokumentstatus:** Demounderlag — nedbantad version, tidsbox 4h
**Datum:** 18 september 2026
**Demo:** kl. 18:00 samma dag

---

## 0. Vad som ändrades mot originalscopet och varför

Originaldokumentet beskrev ett flöde som börjar med **AI-tolkning av en ritning** (PDF/CAD →
identifierade dimensioner). Det är inte byggbart tillförlitligt på 4h.

Vi har istället fått tillgång till två riktiga exempelfiler ur Lindbäcks egen kedja:

- **`components.xml`** — export ur Vertex BD (Lindbäcks eget konstruktionsverktyg). Innehåller
  731 st `FRAMEPIECE`-poster: färdiga, exakta regelbitar med tvärsnitt (`CODE`, t.ex. `45x182`),
  hållfasthetsklass (`MAT_CODE`: C24/C16/C14/GL), kaplängd (`LENGTH`, 47–9725 mm), modul/rum
  (`MODULE_NAME`) och funktion (`USE`).
- **`772_H811_new.ifc`** — 3D-BIM-modellen för samma projekt (IFC4, från samma Vertex BD-export).

Dessutom används publik branschreferensdata från Svenskt Trä (Handelssortering/TräGuiden),
nedladdad till **`./data`**:

- `data/svensktra_standardlangder_mm.csv` — standard handelslängder 1800–5400 mm (300 mm-steg).
  Detta är den riktiga längdaxeln i artikelregistret (§3.2), inte hittepå.
- `data/svensktra_standardbredder_mm.csv` / `data/svensktra_standardtjocklekar_mm.csv` —
  standardbredder/-tjocklekar vid originalsågning (75–250 mm / 19,22,32,38 mm). Kompletterande
  branschreferens — de faktiska regelvirkesdimensionerna (45×95, 45×145 osv.) kommer från
  `components.xml`, inte från dessa filer. Se `data/README.md` för källor och caveat.

**Nyckelfynd:** `IFCBEAM`- och `IFCCOLUMN`-entiteternas `Tag`-fält matchar exakt `OID` på
motsvarande `FRAMEPIECE` i XML:en (t.ex. `Tag='589830'` ↔ `OID="589830"`). Det ger en verifierad,
direkt koppling mellan varje kapbit i materiallistan och dess geometri i 3D-modellen.
Täckningen är uppmätt till **100 %**: alla 731 `FRAMEPIECE`-oid har en träff i modellen, 422 på
`IFCBEAM` och 309 på `IFCCOLUMN`. Båda typerna måste alltså mappas — bara `IFCBEAM` ger 58 %.

**Ytterligare fynd (upptäckt under uppbyggnad):** 43 av de 299 unika kaplängderna i
`components.xml` överstiger 5400 mm — längsta handelslängden i
`data/svensktra_standardlangder_mm.csv` — som mest ca 12,8 m. Sådana behov går inte att täcka
med en enskild inköpt bit utan kräver skarvning av flera handelslängder. Se §3 och §4 för hur
detta hanteras i scopet.

**Konsekvens för scopet:**
- Steg "AI-tolkning av ritning" görs om till **inläsning av redan digitaliserat
  konstruktionsunderlag** (parsning av Vertex BD-export). Detta är en ärlig och realistisk
  beskrivning av vad som faktiskt byggs — och fortfarande det som eliminerar manuell mängdning.
- Kravet på **visuell spårbarhet** blir *skarpt*, inte simulerat: klick på en rad i
  inköpsunderlaget kan highlighta rätt element i en riktig 3D-vy, via OID/Tag-kopplingen.
- Enligt beslut med kund/team är **3D-spårbarheten ett måste** i demot. Om tiden blir knapp
  skärs istället ner i kapoptimeringsalgoritmens sofistikering (se §6, fallback-plan) — inte i
  3D-vyn.

---

## 1. Problembeskrivning

Vägen från konstruktionsunderlag till en korrekt, optimerad inköpsorder innehåller idag manuella
steg: mängder ska härledas, inköp anpassas till artikelregister och tillgängliga handelslängder,
och kapning optimeras. Manuellt arbete ger risk för felbeställningar, suboptimalt nyttjande av
fasta virkeslängder och onödigt spill i fabriksledet.

Demot visar att detta flöde — från strukturerat konstruktionsunderlag till granskningsbart,
spillminimerat inköpsunderlag — kan automatiseras med enkel, transparent logik (matchning +
matematisk optimering), och att resultatet kan verifieras visuellt mot 3D-modellen.

## 2. Roller & Målgrupper

| Roll | Behov | Värde |
|---|---|---|
| Konstruktör | Verifiera att materiallistan stämmer mot 3D-modellen | Litar på underlaget utan manuell dubbelkontroll |
| Inköpare | Få ett färdigt inköpsunderlag mot handelslängder | Rätt volymer, snabbare orderläggning |
| Kapoperatör | Få en exakt, spilloptimerad kaplista | Mindre spill, mindre tid vid sågen |

## 3. Kärnkrav (Must-haves för demot)

1. **Inläsning av konstruktionsunderlag.** Parsa `components.xml` → strukturerad lista av
   materialbehov (tvärsnitt, längd, hållfasthetsklass, modul, funktion).
2. **Artikel-/handelslängdsmatchning.** Gruppera behov per (tvärsnitt, materialklass) och matcha
   mot ett artikelregister vars handelslängder är **riktig data** från
   `data/svensktra_standardlangder_mm.csv` (1800–5400 mm, 300 mm-steg). Endast pris,
   artikelnummer och leveranstid mockas — dessa finns inte öppet tillgängliga (se §4).
3. **Kapoptimering (1D cutting stock), inklusive skarvning av överlånga behov.** Algoritm som
   packar kaplängder mot inköpslängder med hänsyn till sågklingans snittbredd (kerf), och som
   minimerar spill. För kapbehov som överstiger längsta handelslängden (5400 mm, se §0) tillåts
   skarvning: flera inköpta längder summeras (minus kerf per snitt/skarv) tills de täcker
   behovslängden. Sådana rader flaggas tydligt som **skarvade** genom hela kedjan (kaplista →
   inköpsunderlag → export) — algoritmen optimerar ren materialtäckning och spill, den validerar
   inte skarvens strukturella placering (se §4). Ambitionsnivå får skalas ned vid tidsbrist
   (se §6) — men algoritmen ska vara verklig, inte hårdkodad per demo-fil.
4. **Visuell 3D-spårbarhet, åt båda hållen.** Klick på en rad i kaplistan/inköpsunderlaget
   highlightar motsvarande element i en 3D-vy av `772_H811_new.ifc`, via OID↔Tag-kopplingen —
   och klick på ett element i 3D-vyn visar samma bits uppgifter ur materiallistan (oid,
   tvärsnitt, klass, kaplängd, modul, funktion). Detta är projektets skarpaste krav —
   prioriteras vid resurskonflikt.
5. **Granskningsbart inköpsunderlag + spillrapport.** Tabell med inköpslängder, antal, uppskattad
   kostnad och total spillprocent, exporterbar (CSV/PDF-liknande vy räcker för demo).
6. **Valbar exakt optimeringsalgoritm (tillägg, efterarbete 2026-09-18).** Utöver girig FFD
   (kärnkrav 3, `docs/adr.md` ADR-2) ska användaren kunna välja att köra en exakt lösare
   (OR-Tools CP-SAT) för kapoptimeringen istället, för att se den verkliga spillskillnaden mot
   girig FFD. Girig FFD förblir standard och oförändrad — det exakta läget är ett explicit,
   användarinitierat val (inte automatiskt vid sidladdning), eftersom det tar sekunder till
   minuter snarare än millisekunder och inte garanterat hittar en bevisat optimal lösning för de
   större grupperna inom en demo-vänlig tidsgräns. Se `docs/adr.md` ADR-2 (tillägg) för uppmätta
   siffror och `docs/api-contract.md` för kontraktet.

## 4. Vad som INTE ingår (Out of scope)

- **Bildbaserad AI-tolkning av ritningar/CAD.** Ingångsdata är redan strukturerad
  (Vertex BD-export); ingen computer vision byggs.
- **Automatisk direktbeställning hos leverantör.** Inget API/EDI-anrop skickar bindande order.
- **Redigering av CAD/BIM-filer.** Systemet läser `components.xml`/`.ifc`, skriver aldrig till dem.
- **Riktiga priser/artikelnummer/leveranstider.** Mockas som en liten statisk katalog — dessa är
  inte offentligt tillgängliga. Handelslängderna i registret är däremot riktig data (se §0).
- **Icke-träbaserat material.** Endast regelvirke (`FRAMEPIECE`-poster) hanteras.
- **Multi-projekt/multi-fil-stöd.** Demot körs mot exakt dessa två exempelfiler.
- **Strukturell validering av skarvplacering.** Skarvade handelslängder väljs rent på
  materialtäckning (summa ≥ behovslängd, minimerat spill/antal skarvar) — systemet kontrollerar
  inte byggregler för var en skarv får sitta i en bärande regel (momentzoner, skarvavstånd till
  knutpunkter etc.). Skarvade rader flaggas i underlaget för manuell konstruktörsgranskning,
  precis som bildbaserad ritningstolkning (ovan) är en medveten, uttalad avgränsning — inte en
  glömd detalj.

## 5. Vad vi visar kl. 18:00

1. **Inläsning:** `components.xml` laddas, materialbehov extraheras och sammanfattas
   (antal poster, tvärsnitt, klasser, moduler) — visar att "mängdningen" är automatisk.
2. **Artikelmatchning:** Automatiskt genererad materiallista kopplad mot artikelregister med
   Svenskt Träs verkliga standardlängder (`data/svensktra_standardlangder_mm.csv`) och mockade
   priser/artikelnummer.
3. **Kapoptimering + spillrapport:** Kaplista per (tvärsnitt, klass) mot valda inköpslängder,
   med kerf inräknat, och en spillrapport (%). Behov längre än 5400 mm visas som skarvade rader
   (flera inköpslängder), tydligt märkta.
4. **3D-spårbarhet:** `772_H811_new.ifc` visas i en enkel 3D-vy. Klick på en rad i
   kaplistan/inköpsunderlaget highlightar rätt element i modellen (via OID/Tag).
5. **Inköpsunderlag:** Slutlig, granskningsbar tabell redo att exporteras/godkännas.

## 6. Tidsplan (4h) och fallback

| Block | Tid | Innehåll |
|---|---|---|
| 1 | 0:00–0:45 | Parsa `components.xml` → materialbehovslista. Verifiera datamodell (tvärsnitt, klass, längd, modul). |
| 2 | 0:45–1:15 | Läs in `data/svensktra_standardlangder_mm.csv` som handelslängder, lägg på mockat pris/artikelnr, koppla mot behovslistan. |
| 3 | 1:15–2:15 | Kapoptimeringsalgoritm (greedy/First-Fit-Decreasing + kerf) + spillrapport. |
| 4 | 2:15–3:15 | 3D-viewer: ladda `.ifc`, bygg OID↔Tag-mappning, klick-i-tabell → highlight i 3D. |
| 5 | 3:15–3:45 | Slutligt inköpsunderlag + export-vy. |
| 6 | 3:45–4:00 | Buffer, ihopkoppling, demo-genomkörning. |

**Fallback vid tidsbrist:** Skär i Block 3 (kapoptimering) först — gå från optimerad
bin-packing till en enklare girig algoritm eller färre optimeringsvarianter. 3D-spårbarheten
(Block 4) skärs sist, i enlighet med prioriteringsbeslut.

**Teknikförslag (icke-bindande):** ett open source IFC-visningsbibliotek för webben (t.ex.
`web-ifc` / `@thatopen/components`) för att slippa bygga en IFC-parser/3D-renderer från grunden.

## 7. Risker

| Risk | Mitigering |
|---|---|
| IFC-viewer-integration tar längre tid än väntat | Skarpt prioriterad (§6) — får äta tid från optimeringssteget, inte tvärtom |
| `.ifc`-filen (18 MB) är tung att ladda i webbläsare | Ladda/rendera i bakgrunden tidigt i demoflödet, undvik liveparsing på scen |
| ~~OID↔Tag-mappning saknas för vissa element~~ — avskriven, täckningen är uppmätt till 100 % (§0) | Mappa både `IFCBEAM` och `IFCCOLUMN`; enbart `IFCBEAM` täcker 422 av 731 oid |
| Kerf-/optimeringslogik hinner inte bli sofistikerad | Godtagbart för demo — en enkel, korrekt girig algoritm är trovärdig |
| Skarvad bit tolkas nedströms (export, 3D-highlight) som en enda odelad handelslängd | Skarvade rader måste vara explicit märkta i datamodellen genom hela kedjan, inte bara i UI:t, så de inte kan förväxlas med en enskild bit |
| Publiken (byggkunnig) ifrågasätter skarvens strukturella placering på scen | Var transparent: systemet löser materialtäckning, inte skarvregler — flaggat som medveten avgränsning i §4, likt AI-ritningstolkningen |

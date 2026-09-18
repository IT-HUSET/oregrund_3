# Dataspecifikation – Inköps- och spilloptimering (Lindbäcks Bygg, projekt 772_H811)

Status: underlag för implementation. Alla siffror nedan är uppmätta i de faktiska filerna (2026-09-18).

## 1. Källfiler

| Fil | Källa | Roll i lösningen |
|---|---|---|
| `components.xml` | Vertex BD Pro 32.0.8, export 2026-08-27, `PROJ_ID` = 772_H811 | **Sanningskälla för mängder**: varje virkesbit med exakt längd, tvärsnitt och klass |
| `772_H811_new.ifc` | Samma Vertex-projekt, IFC4, ReferenceView_V1.2, enheter i mm | **Visualisering och spårbarhet** i 3D |
| `svensktra_standardlangder_mm.csv` m.fl. | Svenskt Trä | **Artikelregister**: handelslängder 1800–5400 mm i steg om 300 mm |
| `LB-40-0-101.pdf`, `-102.pdf` | AutoCAD-planritningar | Endast referensbild – saknar koppling till objekten |

## 2. Identitet och nycklar – det viktigaste i hela specen

- **`OID` är primärnyckeln.** Den är unik per objekt i XML:en och finns i IFC-objektets `Tag`-attribut (8:e positionen i `IFCBEAM(...)` / `IFCCOLUMN(...)`). 731 av 731 virkesbitar matchar.
- **XML:ens `GUID` ≠ IFC:ns `GlobalId`.** De går inte att konvertera till varandra; använd dem inte som koppling.
- **`ITEM_ID` är inte unik.** Det är ett positions-/typnummer (t.ex. `FD5`); identiska bitar delar det. 303 bitar har samma `COMP_ID`+`ITEM_ID` som en annan bit. Använd det för visning och märkning, inte som nyckel.
- Samma `OID`↔`Tag`-princip gäller på alla nivåer i hierarkin (se §4).

## 3. components.xml

### 3.1 Hierarki

```
COMPONENTS
└── ELEMENTS
    └── WALLELEMENT | FLOORELEMENT | AREAELEMENT      (25 st: 19 väggar, 3 golv, 3 tak)
        └── FRAME | SUBFRAME                         (stomme resp. läkt-/regelskikt)
            └── FRAMEPIECE                           (731 st – en fysisk virkesbit)
```

Elementen innehåller även `SHEET`, `INSULATION_MAT`, `SIDINGBOARD`, `MOUNTINGBOX` m.fl. De ligger utanför scope (trästomme), men `SIDINGBOARD` (329 panelbrädor) har samma fältstruktur som `FRAMEPIECE` om den senare ska med.

Varje nod har XML-attributen `OID`, `GUID`, `SUB_TYPE` och (på barn) `PARENT_OID`. Data ligger i underelementet `<ATTRIBUTES>`.

### 3.2 Fältmappning – `FRAMEPIECE` → intern modell `Piece`

| XML | Exempel | Internt fält | Typ | Kommentar |
|---|---|---|---|---|
| `@OID` | `589830` | `piece_id` | string | Primärnyckel, = IFC `Tag` |
| `@PARENT_OID` | `215942` | `frame_id` | string | FRAME/SUBFRAME; = IFC `IfcBuildingElementPart.Tag` |
| `@GUID` | `f5b94e9a-…` | `vertex_guid` | string | Spara, men använd inte för koppling |
| `ITEM_ID` | `FD5` | `position` | string | Etikett vid såg och i kaplista |
| `COMP_ID` | `GOLV-131` | `element_id` | string | Elementnamn, 25 unika |
| `MODULE_NAME` | `131` | `module` | string | Volymmodul |
| `MODULE_FLAT` | `TVÄTT` | `room` | string | Rum/lägenhet |
| `STR_TYPE` | `FLOOR`, `WALL/EXT` | `structure_type` | string | |
| `USE` | `ÖPPNINGSREGEL` | `function` | string | Styr filtrering, se §5 |
| `CODE` | `45x182` | `section_label` | string | Visning; beräkna från WIDTH/HEIGHT |
| `WIDTH` | `45` | `thickness_mm` | float | Tjocklek |
| `HEIGHT` | `182` | `width_mm` | float | Bredd |
| `LENGTH` | `255.0` | `length_mm` | float | Färdig kaplängd; max 1 decimal, min 47 mm |
| `MAT_CODE` | `C24` | `grade` | string | C14, C16, C24, GL |
| `SA_ID` | `130-Y-01.OPNG.1` | `subassembly` | string? | Öppningspaket; saknas oftast |
| `START_ANGX/Y`, `END_ANGX/Y` | `0.00` | – | float | Alla 0 → rakkap. Validera och larma om ≠ 0 |
| `CUTMODE` | `1` | – | – | Alltid 1 i detta projekt |
| `PIECE_TYPE`, `SEC_WEIGHT`, `MOUNT`, `BOM_PHASE` | | – | | Behövs ej för optimeringen |

**Tvärsnittsnyckel:** `section = f"{thickness_mm:g}x{width_mm:g}"`, `material_key = f"{section} {grade}"`, t.ex. `45x220 C24`.

### 3.3 Elementnivå (`WALLELEMENT` m.fl.) → `Element`

| XML | Internt | Kommentar |
|---|---|---|
| `@OID` | `element_oid` | = IFC `IfcElementAssembly.Tag` |
| `ITEM_ID` | `element_id` | Samma värde som barnens `COMP_ID` |
| `DIMMX/Y/Z` | `dims_mm` | Elementets ytterdimensioner |
| `MODULE_NAME`, `MODULE_FLAT` | `module`, `room` | |

## 4. IFC-filen

### 4.1 Relevanta entiteter

| IFC-entitet | Antal | Motsvarar i XML | Koppling |
|---|---|---|---|
| `IfcElementAssembly` | 25 | WALLELEMENT/FLOORELEMENT/AREAELEMENT | `Tag` = element-`OID`, `Name` = `COMP_ID` (ibland med `*`) |
| `IfcBuildingElementPart` | – | FRAME/SUBFRAME | `Tag` = `PARENT_OID`, `Name` t.ex. `STOMME-182` |
| `IfcBeam` | 422 | FRAMEPIECE | `Tag` = `OID` |
| `IfcColumn` | 309 | FRAMEPIECE | `Tag` = `OID` |

Hierarkin går via `IfcRelAggregates`: `IfcElementAssembly` → `IfcBuildingElementPart` → `IfcBeam`/`IfcColumn`.

### 4.2 Fält per virkesbit i IFC

| IFC-källa | Exempel | Användning |
|---|---|---|
| `GlobalId` | `0GO7ParmT1Tv4$2Iz4gRMP` | Id i IFC-viewern (highlight/select) |
| `Name` | `FD5 Opening header beam 45x182 C24` | Tooltip; innehåller alltid `ITEM_ID` (verifierat 731/731) |
| `Tag` | `589830` | **Kopplingsnyckel till XML** |
| `Pset_BeamCommon.Reference` | `FD5` | = `ITEM_ID` |
| `Qto_BeamBaseQuantities.Length` | `254.999…` | Kontrollvärde; avrunda till 0,1 mm, jämför mot XML `LENGTH` |

I viewern (web-ifc / That Open Components) byggs vid inläsning en uppslagstabell `Tag → expressID` för både beams och columns; resten av appen pratar bara `piece_id`.

### 4.3 Parsningsdetaljer

- IFC-strängar använder STEP-escaping (`\X\F6` = ö). Avkoda innan visning.
- XML är UTF-8 med entiteter (`&#196;` = Ä); en vanlig XML-parser hanterar detta.
- IFC-filen är 18 MB med ~105 000 facetter. Ladda den en gång och cacha.

## 5. Filtrering och normalisering (731 bitar in → optimeringsunderlag ut)

| Regel | Omfattning | Åtgärd |
|---|---|---|
| `MAT_CODE = GL` (`LIMTRÄREGEL`, `LIMTRÄBALK`) | 4 | Exkludera från kapoptimering; lista separat som "beställs i hel längd" |
| `USE = SHIMS` | 3 | Exkludera (inkl. C14 med tjocklek 9,76/9,78/17,55 mm) |
| Tjocklek 90 mm (`SAMMANSATTSTOLPE`, `LYFTSTOLPE`, `LYFTSTOLPE HÖG`) | 40 | **Beslut krävs**: dela till 2 × 45 mm med samma längd (behåll `piece_id` + suffix `-a`/`-b`), eller behandla som egen artikel |
| `LENGTH > 5400` | 50 | **Beslut krävs**: längre handelslängder i registret, skarvning, eller "hel längd"-kategori. Gäller främst hammarband, syll, kantregel, korsregel och läkt, upp till 9 725 mm |
| Läkt 12×45, 28×70 och korsregel 34×45 | 118 | Behåll; egna artiklar |
| Vinklar ≠ 0 | 0 | Validering: larma om det dyker upp i andra projekt |

Efter normalisering grupperas behovet per `material_key` (tvärsnitt + klass). Varje grupp optimeras separat.

## 6. Artikelregister (mockat från Svenskt Trä)

En artikel = tvärsnitt × klass × handelslängd.

| Fält | Exempel | Källa |
|---|---|---|
| `article_no` | `LB-C24-045220-4800` | Genererat: `LB-{grade}-{t:03d}{w:03d}-{length}` |
| `grade` | `C24` | Från projektdata |
| `thickness_mm`, `width_mm` | 45, 220 | Från projektdata (Svenskt Träs bredd-/tjocklekstabeller gäller originalsågat och används inte) |
| `length_mm` | 4800 | Svenskt Trä: 1800–5400, steg 300 |
| `price_per_m` | – | **Mock** |
| `lead_time_days` | – | **Mock** (valfritt, REQ-2.4 är bortvald) |

Registret genereras för varje `material_key` som förekommer i projektet.

## 7. Optimeringens in- och utdata

**Input per `material_key`:** lista av `(piece_id, length_mm)`, tillgängliga `stock_lengths_mm`, `kerf_mm` (standard 4, konfigurerbart 4–5).

**Output – `CutPlan`:** en lista av inköpta virken där varje virke har:

| Fält | Beskrivning |
|---|---|
| `stock_id` | Löpnummer, t.ex. `C24-45x220-#07` |
| `article_no` | Inköpt artikel |
| `cuts` | Ordnad lista av `piece_id` |
| `used_mm`, `kerf_total_mm`, `offcut_mm` | Förbrukat, sågsnitt, restbit |

Villkor: `sum(längder) + kerf × antal_snitt ≤ stock_length`. Antal snitt = antal bitar, eller antal bitar − 1 om sista biten går jäms med virkets ände. Välj en konvention och dokumentera den.

**Härledda utdata:**

- **Kaplista (REQ-3.4):** en rad per `(stock_id, cut)`: virke, artikel, position (`ITEM_ID`), `piece_id`, längd, element, rum.
- **Inköpsunderlag:** aggregering av `CutPlan` per `article_no`: antal, total längd, (mock)kostnad.
- **Spillrapport (REQ-4.4):** nyttjandegrad %, totalt spill i m och %, kostnad. Jämförs mot en **baslinje** = varje bit köps i närmast längre handelslängd, en bit per virke. Baslinjen ska vara fastställd innan demon.

## 8. Spårbarhetskedja

```
IFC-objekt (GlobalId) ⇄ Tag = OID = piece_id ⇄ kaplista-rad ⇄ stock_id ⇄ inköpsrad (article_no)
```

- Klick på kaplista-rad → highlight via `piece_id` → `expressID`.
- Klick på inköpsrad → highlight alla `piece_id` i alla `stock_id` för artikeln.
- Klick på objekt i 3D → visa `stock_id`, position i virket och artikel.
- Fysisk märkning vid såg: `ITEM_ID` + `piece_id` (ev. QR-kod med `piece_id`).

## 9. Öppna beslut

1. Hantering av bitar > 5 400 mm (§5).
2. Uppdelning av 90 mm-stolpar (§5).
3. Kerf-konvention (snitt per bit eller per bit − 1) och standardvärde.
4. Baslinje för spillrapporten.
5. Ingår `SIDINGBOARD` (panelbrädor) eller inte.

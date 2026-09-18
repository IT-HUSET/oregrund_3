# API-kontrakt — backend ↔ frontend

Detta är källan till sanning för gränssnittet mellan backend (`backend/`) och frontend
(`frontend/`), enligt `docs/adr.md` ADR-1. Två språk (Python/Pydantic, TypeScript) delar inga
typer automatiskt — ändras ett fält här måste **både** `backend/app/models.py` **och**
`frontend/src/api/types.ts` uppdateras i samma commit, annars går kontraktet sönder tyst.

Backend genererar dessutom interaktiv dokumentation automatiskt från `models.py` på
`http://localhost:8000/docs` (Swagger UI) och `/openapi.json` — använd den för att verifiera
exakta fältnamn/typer när du är osäker, den här filen är den läsbara sammanfattningen.

**Status:** Implementerat. Alla endpoints svarar med riktig data ur `data/components.xml`
(731 rader) och full FFD-kapoptimering — fixture-läget är borta. Två export-endpoints
(`/api/purchase-order.csv`, `/api/cut-list.csv`) har tillkommit, se nedan.

## Gemensamt

- Alla längder/mått i **mm**, som float. `width_mm`/`height_mm` är float (inte int): tre
  SHIMS-bitar i `components.xml` har tjocklek 9,76 / 9,78 / 17,55 mm.
- `oid` är strängen från `FRAMEPIECE OID` i `components.xml` — samma värde som `IFCBEAM.Tag` i
  `772_H811_new.ifc` (se `docs/prd.md` §0). Detta är nyckeln frontend använder för 3D-highlight
  (inkrement 4, `docs/adr.md` ADR-3) — backend öppnar aldrig `.ifc`-filen själv.
- Kerf (sågklingans snittbredd) är `3.0` mm, satt i `backend/app/config.py::KERF_MM`
  (`docs/adr.md` ADR-2).
- Pris, artikelnummer och leveranstid är **mockade** (inte offentligt tillgänglig data, se
  `docs/prd.md` §4/§0) — handelslängderna är riktig data från
  `data/svensktra_standardlangder_mm.csv`.
- **Skarvning:** 43 av 299 unika kaplängder i `components.xml` överstiger 5400 mm (längsta
  handelslängden) och kräver att flera inköpta längder skarvas ihop (`docs/prd.md` §0/§3.3). Ett
  sådant behov täcks av *flera* `cuts[]`-rader (en per köpt bit den är skarvad ur), markerade
  `spliced: true`, i stället för en enda rad. Algoritmen optimerar bara materialtäckning/spill —
  den validerar inte skarvens strukturella placering (`docs/prd.md` §4, medveten avgränsning).

---

## `GET /api/bom`

Inkrement 1. Alla `FRAMEPIECE`-poster ur `components.xml`, oparsat vidare.

```json
{
  "count": 731,
  "items": [
    {
      "oid": "589830",
      "item_id": "FD5",
      "code": "45x182",
      "width_mm": 45.0,
      "height_mm": 182.0,
      "length_mm": 255.0,
      "mat_code": "C24",
      "module_name": "131",
      "module_flat": "TVÄTT",
      "use": "ÖPPNINGSREGEL",
      "bom_phase": "1. Floor"
    }
  ]
}
```

Kontroll (`docs/plan.md` #1): `count == 731`; filtrera på `code == "45x182"` → 72 träffar.

---

## `GET /api/bom/groups`

Inkrement 2. BOM grupperad per (`code`, `mat_code`), matchad mot handelslängder. Detta är en
tredje endpoint utöver skissen i `docs/adr.md` (som bara nämner `/api/bom` och
`/api/purchase-order`) — den behövs för att visa den grupperade vyn i inkrement 2 *innan*
kapoptimeringen (inkrement 3) är klar, utan att hitta på nya krav (behovet står redan i
`docs/prd.md` §3.2/§5.2).

```json
{
  "groups": [
    {
      "code": "45x182",
      "mat_code": "C24",
      "piece_count": 72,
      "total_length_mm": 87400.0,
      "pieces": [
        { "oid": "589830", "length_mm": 255.0 }
      ],
      "available_trade_lengths_mm": [1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400],
      "excluded_reason": null
    }
  ]
}
```

`excluded_reason` är satt (i stället för `null`) för grupper som inte kapoptimeras — limträ
och kilar, se `data/dataspec.md` §5 och "Undantagna bitar" nedan. Frontend visar flaggan, den
härleder aldrig regeln själv.

Kontroll (`docs/plan.md` #2): gruppen `45x182`/`C24` har `piece_count == 72` och listar
handelslängderna 1800–5400 mm.

---

## `GET /api/purchase-order`

Inkrement 3 (kapoptimering + spillrapport + inköpsunderlag) och grunden för inkrement 4
(`oid` följer med hela vägen ner i `bars[].cuts[]`).

```json
{
  "kerf_mm": 3.0,
  "groups": [
    {
      "code": "45x182",
      "mat_code": "C24",
      "waste_percent": 6.7,
      "bars": [
        {
          "purchase_length_mm": 3000,
          "cuts": [
            { "oid": "589830", "length_mm": 255.0 },
            { "oid": "589832", "length_mm": 3110.0 }
          ],
          "used_length_mm": 3365.0,
          "kerf_total_mm": 6.0,
          "waste_mm": -371.0
        },
        {
          "purchase_length_mm": 5400,
          "cuts": [
            {
              "oid": "591200",
              "length_mm": 5397.0,
              "spliced": true,
              "segment_index": 1,
              "segment_count": 2
            }
          ],
          "used_length_mm": 5400.0,
          "kerf_total_mm": 3.0,
          "waste_mm": 0.0
        },
        {
          "purchase_length_mm": 4500,
          "cuts": [
            {
              "oid": "591200",
              "length_mm": 4328.0,
              "spliced": true,
              "segment_index": 2,
              "segment_count": 2
            }
          ],
          "used_length_mm": 4331.0,
          "kerf_total_mm": 3.0,
          "waste_mm": 169.0
        }
      ],
      "splices": [
        {
          "oid": "591200",
          "total_length_mm": 9725.0,
          "segment_count": 2,
          "purchase_lengths_mm": [5400, 4500],
          "joint_count": 1
        }
      ]
    }
  ],
  "order_lines": [
    {
      "code": "45x182",
      "mat_code": "C24",
      "purchase_length_mm": 3000,
      "quantity": 40,
      "article_number": "MOCK-45x182-C24-3000",
      "price_per_unit_sek": 187.5,
      "lead_time_days": 5,
      "total_price_sek": 7500.0
    }
  ],
  "summary": {
    "total_bars": 525,
    "total_needed_length_mm": 1865037.7,
    "total_purchased_length_mm": 1940700.0,
    "total_waste_percent": 3.9,
    "total_cost_sek": 71764.8,
    "spliced_piece_count": 50,
    "total_joints": 50,
    "baseline": {
      "total_bars": 774,
      "total_purchased_length_mm": 2199600.0,
      "total_waste_percent": 15.21,
      "total_cost_sek": 81313.2,
      "saved_length_mm": 258900.0,
      "saved_cost_sek": 9548.4,
      "saved_percent": 11.77
    }
  }
}
```

**Nya fält (skarvning):**
- `cuts[].spliced` — `true` om denna rad bara är ett *segment* av en kapbit som behöver fler än
  en inköpt längd (utelämnas/`false` för normala rader). `segment_index`/`segment_count` följer
  med när `spliced` är sant (1-baserat, t.ex. 1/2 och 2/2 ovan).
- `groups[].splices` — en rad per skarvat `oid` i gruppen: `total_length_mm` är kapbitens fulla
  behovslängd (samma som i `/api/bom`), `purchase_lengths_mm` de inköpta längderna den byggs av,
  `joint_count` antal skarvar (`segment_count - 1`). Ingen extra kerf modelleras för själva
  skarven i det här demot — varje segments egen kerf är redan medräknad i dess bars
  `kerf_total_mm`. Se `docs/prd.md` §3.3/§4: algoritmen validerar inte var skarven strukturellt
  får sitta.
- `summary.spliced_piece_count` / `summary.total_joints` — aggregat för hela inköpsunderlaget,
  till spillrapporten.
- `summary.baseline` — den **ooptimerade** jämförelsen som spillrapporten mäts mot
  (`data/dataspec.md` §7): varje kapbit köpt i närmast längre handelslängd, en bit per stång.
  `saved_*` är skillnaden mot det optimerade resultatet. Fältet är `null` bara om underlaget är
  tomt.

## Undantagna bitar

`/api/bom` och `/api/bom/groups` innehåller **alla** 731 `FRAMEPIECE`. Kapoptimeringen i
`/api/purchase-order` hoppar däremot över 7 av dem enligt `data/dataspec.md` §5: 4 limträbitar
(`MAT_CODE = GL`, beställs i hel längd) och 3 kilar (`USE = SHIMS`). De syns alltså i
materialbehovet men har inga `cuts[]`-rader.

---

## `GET /api/purchase-order.csv` och `GET /api/cut-list.csv`

Inkrement 3, exportvyn (`docs/prd.md` §3.5). Samma siffror som JSON-svaret — exporten
formaterar bara om dem, den räknar aldrig om något.

- **`/api/purchase-order.csv`** — en rad per inköpsartikel plus en summeringssektion med
  spillrapporten (spill %, kostnad, antal skarvade bitar, kerf).
- **`/api/cut-list.csv`** — en rad per kapbit: stång-id (numrerat per grupp från `#001`, samma
  etikett som UI:t visar), tvärsnitt, handelslängd, position i
  stången, `OID`, `ITEM_ID`, kaplängd, modul, rum och funktion. Kolumnen **`Skarv`** är tom för
  en vanlig bit och `"2 av 3"` för ett skarvsegment, så en skarvad rad aldrig kan läsas som en
  odelad längd vid sågen (`docs/prd.md` §7).

Båda använder `;` som separator, decimalkomma och inleds med UTF-8 BOM — annars avkodar Excel
på Windows filen med ANSI-kodsidan och åäö blir mojibake.

Kontroll (`docs/plan.md` #3): för en given grupp, `sum(cuts.length_mm) + kerf_total_mm + waste_mm
== used_length_mm <= purchase_length_mm` (materialet balanserar) — gäller per bar oavsett
`spliced`. `oid` i `bars[].cuts[]` är samma `oid` som i `/api/bom`, vilket är vad inkrement 4 slår
upp mot IFC `Tag` (en skarvad kapbit highlightar alltså flera `bars[].cuts[]`-rader men ett enda
element i 3D-vyn). För skarvade `oid`: `sum(cuts med detta oid.length_mm) == splices[].total_length_mm`.

---

## Ändra kontraktet

1. Uppdatera denna fil (fälten + exempel-JSON).
2. Uppdatera `backend/app/models.py` (Pydantic) i samma commit.
3. Uppdatera `frontend/src/api/types.ts` (TS-interfaces) i samma commit.
4. Nämn ändringen i PR/commit-meddelandet så den andra sidan ser den.

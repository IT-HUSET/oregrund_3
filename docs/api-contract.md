# API-kontrakt — backend ↔ frontend

Detta är källan till sanning för gränssnittet mellan backend (`backend/`) och frontend
(`frontend/`), enligt `docs/adr.md` ADR-1. Två språk (Python/Pydantic, TypeScript) delar inga
typer automatiskt — ändras ett fält här måste **både** `backend/app/models.py` **och**
`frontend/src/api/types.ts` uppdateras i samma commit, annars går kontraktet sönder tyst.

Backend genererar dessutom interaktiv dokumentation automatiskt från `models.py` på
`http://localhost:8000/docs` (Swagger UI) och `/openapi.json` — använd den för att verifiera
exakta fältnamn/typer när du är osäker, den här filen är den läsbara sammanfattningen.

**Status:** Boilerplate-läge. Alla tre endpoints svarar just nu med fixture-data
(`backend/app/services/fixtures.py`) — riktiga värden (731 rader, full FFD-optimering) kopplas in
per inkrement enligt `docs/plan.md`. Response-formen ändras inte när det sker, bara innehållet.
Frontend kan alltså byggas klart mot detta kontrakt redan nu.

## Gemensamt

- Alla längder/mått i **mm** (float för längder som kan ha decimaler, int för tvärsnitt
  bredd/höjd — utom `width_mm`, som är float: tre `SHIMS`-poster (`MAT_CODE=C14`) har en
  decimal `WIDTH`, t.ex. `9.76252`).
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
      "width_mm": 45,
      "height_mm": 182,
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
      "available_trade_lengths_mm": [1800, 2100, 2400, 2700, 3000, 3300, 3600, 3900, 4200, 4500, 4800, 5100, 5400]
    }
  ]
}
```

Kontroll (`docs/plan.md` #2): gruppen `45x182`/`C24` har `piece_count == 72` och listar
handelslängderna 1800–5400 mm.

---

## `GET /api/purchase-order`

Inkrement 3 (kapoptimering + spillrapport + inköpsunderlag) och grunden för inkrement 4
(`oid` följer med hela vägen ner i `bars[].cuts[]`).

Query-parametern `algorithm` och fälten `algorithm`/`optimal`/`solve_time_ms` nedan implementerar
kärnkrav 6 (`docs/prd.md` §3.6, `docs/adr.md` ADR-2-tillägget).

**Query-parameter:** `algorithm` (valfri, sträng): `"greedy"` (default, oförändrat beteende) |
`"exact"`. Vid `"exact"` körs OR-Tools CP-SAT per grupp med en tidsgräns
(`backend/app/config.py`, inte hårdkodad inline) — svarstiden blir sekunder till minuter
istället för millisekunder (se ADR-2-tillägget för uppmätta tal), så detta ska vara ett
explicit, användarinitierat val i UI:t (t.ex. en knapp med väntetid/spinner), inte något som
körs vid vanlig sidladdning.

```json
{
  "kerf_mm": 3.0,
  "algorithm": "greedy",
  "groups": [
    {
      "code": "45x182",
      "mat_code": "C24",
      "waste_percent": 6.7,
      "algorithm": "greedy",
      "optimal": true,
      "solve_time_ms": 0.3,
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
    "total_bars": 210,
    "total_needed_length_mm": 612345.0,
    "total_purchased_length_mm": 654300.0,
    "total_waste_percent": 6.4,
    "total_cost_sek": 452310.0,
    "spliced_piece_count": 43,
    "total_joints": 46
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

**Nya fält (valbar exakt lösare, `docs/prd.md` §3.6, `docs/adr.md` ADR-2-tillägget):**
- Toppnivå `algorithm` — vilket läge svaret faktiskt kördes med (`"greedy"` | `"exact"`), ekar
  tillbaka query-parametern.
- `groups[].algorithm` — samma värde per grupp (alla grupper körs med samma läge i en och samma
  request).
- `groups[].optimal` — `true` om lösningen är bevisat optimal (alltid `true` för `greedy`, som
  inte gör optimalitetsanspråk men heller inte har en tidsgräns att missa; för `exact`: `true` om
  CP-SAT löste till bevisad optimalitet inom tidsgränsen, annars `false` — "bästa hittade", se
  ADR-2). UI:t ska visa detta tydligt, inte påstå optimalt när det bara är bäst-hittills.
- `groups[].solve_time_ms` — hur lång tid grupplösningen tog, för transparens i UI:t (girig är
  ~0, exakt kan vara sekunder).

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

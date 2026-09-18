# frontend

Vite + React + TypeScript. Ren klient mot backend-API:et (`../backend/`) — se
`../docs/api-contract.md` för kontraktet och `../docs/adr.md` ADR-1/ADR-3 för varför.

## Kör

```
npm install
cp ../data/772_H811_new.ifc public/        # 3D-modellen, gitignorerad kopia
cp node_modules/web-ifc/web-ifc.wasm public/   # IFC-parsern (WASM)
npm run dev     # http://localhost:5173, proxyar /api mot http://localhost:8000 (vite.config.ts)
```

De två `cp`-raderna behövs en gång efter en fresh clone: Vite serverar bara `public/`, och
`data/` ligger utanför `frontend/`. Kopiorna är gitignorerade -- `data/` är källan.

Kör `../backend/` parallellt (se `../backend/README.md`) för att få riktig data.

## Struktur

```
src/
  api/
    types.ts       TS-spegel av backend/app/models.py -- API-kontraktet
    client.ts       fetch-wrappers per endpoint
    useFetch.ts      delad loading/error/data-hook
  ifc/
    loadIfcModel.ts  web-ifc -> three.js-scen + expressID<->Tag-kartorna
  format.ts       sv-SE-formatering av mm/meter/SEK/procent
  csv.ts          CSV-export (semikolon, decimalkomma, UTF-8-BOM)
  components/
    BomTable.tsx          inkrement 1 -- GET /api/bom
    BomGroupsView.tsx     inkrement 2 -- GET /api/bom/groups
    PurchaseOrderView.tsx inkrement 3 -- GET /api/purchase-order
    IfcViewer.tsx          inkrement 4 -- 3D-vy, dubbelriktad OID-spårbarhet
  App.tsx           flikar mellan vyerna + selectedOid-state för 3D-highlight
```

## Status

Alla fyra inkrement i `../docs/plan.md` är byggda mot riktig backend-data.

3D-vyn laddar modellen en gång per sidladdning och är alltid monterad, så de 18 MB parsas i
bakgrunden medan man tittar på tabellerna (`../docs/prd.md` §7). Highlight ritas utan djuptest
-- reglarna sitter inuti väggarna och syns annars inte. Spårbarheten täcker `IFCBEAM` +
`IFCCOLUMN` (alla 731 OID); plattor och skivor renderas men saknar Tag.

## Testa

Ingen testrunner är tillagd än (boilerplate-läge). `npm run build` typkontrollerar
(`tsc -b`) och bygger, `npm run lint` kör oxlint.

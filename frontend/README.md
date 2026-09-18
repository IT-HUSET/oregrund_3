# frontend

Vite + React + TypeScript. Ren klient mot backend-API:et (`../backend/`) — se
`../docs/api-contract.md` för kontraktet och `../docs/adr.md` ADR-1/ADR-3 för varför.

## Kör

```
npm install
npm run dev     # http://localhost:5173, proxyar /api mot http://localhost:8000 (vite.config.ts)
```

Kör `../backend/` parallellt (se `../backend/README.md`) för att få riktig data.

## Struktur

```
src/
  api/
    types.ts       TS-spegel av backend/app/models.py -- API-kontraktet
    client.ts       fetch-wrappers per endpoint
    useFetch.ts      delad loading/error/data-hook
  components/
    BomTable.tsx          inkrement 1 -- GET /api/bom
    BomGroupsView.tsx     inkrement 2 -- GET /api/bom/groups
    PurchaseOrderView.tsx inkrement 3 -- GET /api/purchase-order
    IfcViewer.tsx          inkrement 4 -- platshållare, se docs/adr.md ADR-3
  App.tsx           flikar mellan vyerna + selectedOid-state för 3D-highlight
```

## Status

Boilerplate-läge: backend svarar med fixture-data (`backend/app/services/fixtures.py`), så
tabellerna visar en handfull riktiga rader ur `data/components.xml`, inte de fulla 731. Formen
på svaren ändras inte när backend kopplar in riktig parsning/optimering.

`IfcViewer.tsx` är en platshållare -- riktig 3D-rendering (web-ifc + three.js mot
`data/772_H811_new.ifc`) är inkrement 4, se `../docs/plan.md`.

## Testa

Ingen testrunner är tillagd än (boilerplate-läge). `npm run build` typkontrollerar
(`tsc -b`) och bygger, `npm run lint` kör oxlint.

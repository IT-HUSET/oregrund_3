# frontend

Vite + React + TypeScript. Ren klient mot backend-API:et (`../backend/`) — se
`../docs/api-contract.md` för kontraktet och `../docs/adr.md` ADR-1/ADR-3 för varför.

## Kör

```
npm install
npm run dev     # http://localhost:5173, proxyar /api mot http://localhost:8000 (vite.config.ts)
```

Kör `../backend/` parallellt (se `../backend/README.md`) för att få riktig data.

**Node 20.19+ krävs** (Vite 8). På Node 18 kraschar bygget i rolldown. Har du nvm:
`nvm use 20`. Har du installerat beroendena med fel Node-version behöver
`node_modules/` och `package-lock.json` tas bort och `npm install` köras om — npm hoppar
annars över den plattformsspecifika rolldown-binären.

3D-vyn hämtar `../data/772_H811_new.ifc` (18 MB) via en liten dev-middleware i
`vite.config.ts` som serverar repots `data/`-mapp read-only under `/data`. `web-ifc`s
WASM-binär kopieras till `public/wasm/` av `npm run sync-wasm`, som körs automatiskt före
`dev` och `build`.

## Struktur

```
src/
  api/
    types.ts       TS-spegel av backend/app/models.py -- API-kontraktet
    client.ts       fetch-wrappers per endpoint
    useFetch.ts      delad loading/error/data-hook
  format.ts        svenska tal-/valutaformaterare
  ifc/
    loadIfcModel.ts  laddar .ifc, bygger three.js-scen + Tag<->expressID-karta
  components/
    BomTable.tsx          inkrement 1 -- GET /api/bom, med filter på tvärsnitt/klass
    BomGroupsView.tsx     inkrement 2 -- GET /api/bom/groups, expanderbara grupper
    PurchaseOrderView.tsx inkrement 3 -- kaplista, spillrapport, inköpsunderlag, CSV-export
    IfcViewer.tsx         inkrement 4 -- 3D-vy med OID-highlight (docs/adr.md ADR-3)
  App.tsx           flikar mellan vyerna + selectedOid-state för 3D-highlight
scripts/
  verify-ifc-mapping.mjs  kontrollerar OID<->Tag mot den riktiga IFC-filen
```

Flikarna monteras alla tre och döljs med CSS — 3D-vyn ligger kvar så att den 18 MB stora
modellen laddas en enda gång (`../docs/prd.md` §7).

## Status

Klar. Alla fyra inkrementen är byggda:

- **Materialbehov** — 731 rader ur `components.xml`, filtrerbara på tvärsnitt, klass och fritext.
- **Artikelmatchning** — 24 grupper mot Svenskt Träs handelslängder, expanderbara.
- **Inköpsunderlag** — kaplista med stångvisualisering, spillrapport mot ooptimerad baslinje,
  skarvade bitar märkta, CSV-export av både underlag och kaplista.
- **3D-spårbarhet** — klick på en kapbit highlightar rätt element i `772_H811_new.ifc`; klick i
  3D-vyn väljer tillbaka biten i tabellen.

## Testa

```
npm run build       # tsc -b + vite build (typkontroll)
npm run lint        # oxlint
npm run verify:ifc  # OID<->Tag mot den riktiga IFC-filen (docs/plan.md #4)
```

`verify:ifc` jämför även mot `/api/bom` om backend är igång på :8000.

# Technology Stack

## Languages
| Language   | Version | Notes |
|------------|---------|-------|
| Python     | 3.x (`backend/`) | Backend, FastAPI |
| TypeScript | ~6.0.2 (`frontend/`) | Frontend, strict via `tsc -b` |

## Frameworks & Libraries
| Name | Version | Purpose |
|------|---------|---------|
| FastAPI | 0.115.6 | Backend web framework / JSON API |
| Pydantic | 2.10.4 | Request/response schemas (`backend/app/models.py`) |
| uvicorn | 0.34.0 (`[standard]`) | ASGI server |
| pytest | 8.3.4 | Backend test runner |
| httpx | 0.28.1 | Test client for FastAPI endpoints |
| React | ^19.2.8 | Frontend UI |
| react-dom | ^19.2.8 | Frontend DOM rendering |
| Vite | ^8.3.0 | Frontend dev server / build |
| web-ifc | 0.0.77 | IFC-parsning (WASM) av `772_H811_new.ifc`, klientsidan (`docs/adr.md` ADR-3) |
| three.js | 0.186.0 | 3D-rendering, picking och highlight (`frontend/src/ifc/loadIfcModel.ts`) |

## Infrastructure
| Service | Purpose | Notes |
|---------|---------|-------|
| Lokal dev-server (uvicorn) | Backend, port 8000 | `uvicorn app.main:app --reload --port 8000` |
| Lokal dev-server (Vite) | Frontend, port 5173 | Proxyar `/api` mot backend |

## External Services
_Inga — demot körs helt lokalt mot statiska filer (`components.xml`, `772_H811_new.ifc`,
`data/svensktra_*.csv`). Inga priser/artikelnummer hämtas från extern källa (mockas, se
`docs/prd.md` §4)._

## Dev Tools
| Tool | Purpose | Config |
|------|---------|--------|
| pytest | Backend-tester | `backend/pytest.ini` |
| oxlint | Frontend-lint | `frontend/package.json` (`npm run lint`) |
| tsc | Frontend type-check (del av build) | `frontend/package.json` (`npm run build`) |

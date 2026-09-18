# Key Development Commands

## Running the Application
| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload --port 8000` (in `backend/`) | Start backend dev server |
| `npm run dev` (in `frontend/`) | Start frontend dev server, proxies `/api` to backend |

Application URL: `http://localhost:5173` (frontend) / `http://localhost:8000/docs` (backend Swagger UI)

## Code Quality (Formatting, Linting, Type Checking)
| Command | Description |
|---------|-------------|
| `npm run lint` (in `frontend/`) | Lint frontend (oxlint) |
| `npm run build` (in `frontend/`) | Type-check (`tsc -b`) then build |

## Testing
| Command | Description |
|---------|-------------|
| `pytest` (in `backend/`) | Run all backend tests |
| `pytest tests/test_bom.py` (in `backend/`) | Run a single test file |
| `pytest tests/test_bom.py::test_name` (in `backend/`) | Run a single test |

Kontroll per inkrement (automattest **och** manuellt klicksteg) står i `docs/plan.md`,
kolumnen "Kontroll (test \| klick)". Ett inkrement räknas inte klart förrän båda är gjorda.

## Build & Deployment
_Ingen deploy — lokal demoprototyp. `npm run build` bygger frontend statiskt om det behövs._

## Visual Validation
| Command / Tool | Description |
|-----------------|-------------|
| `npm run dev` + öppna `http://localhost:5173` | Manuell verifiering mot klicksteget i `docs/plan.md` |

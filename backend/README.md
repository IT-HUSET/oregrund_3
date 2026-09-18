# backend

FastAPI + Pydantic. Se `../docs/api-contract.md` för API-kontraktet och `../docs/adr.md` för
arkitekturbeslut (ADR-1/2/3).

## Kör

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Testa

```
pytest
```

## Status

Klar. Alla endpoints svarar med riktig data ur `../data/components.xml` (731 `FRAMEPIECE`) och
kör den riktiga FFD-kapoptimeringen. Fixture-läget är borttaget.

Nyckeltal för demot (`GET /api/purchase-order`): **3,90 % spill** över 525 inköpta stänger, mot
**15,21 %** för den ooptimerade baslinjen (en handelslängd per bit) — en besparing på 258,9 m
virke och ca 9 548 SEK i mockat pris. 50 kapbitar är längre än 5400 mm och skarvas.

## Endpoints

| Endpoint | Innehåll |
|---|---|
| `GET /api/bom` | Alla 731 kapbitar ur `components.xml` |
| `GET /api/bom/groups` | Grupperat per (tvärsnitt, klass) + handelslängder ur CSV:n |
| `GET /api/purchase-order` | Kaplista, skarvar, inköpsrader, spillrapport + baslinje |
| `GET /api/purchase-order.csv` | Inköpsunderlaget som CSV (svensk Excel: `;` och decimalkomma) |
| `GET /api/cut-list.csv` | Kaplistan som CSV, en rad per kapbit, skarvsegment märkta |
| `GET /api/health` | Hälsokoll |

Limträ (`MAT_CODE = GL`, 4 st) och kilar (`USE = SHIMS`, 3 st) ingår i BOM:en men
kapoptimeras inte (`../data/dataspec.md` §5).

## Struktur

```
app/
  main.py               FastAPI-app, CORS, routrar
  config.py             Sökvägar (data/), KERF_MM
  models.py             Pydantic-scheman -- API-kontraktet
  routers/               GET-endpoints, tunna, anropar services/
  services/
    xml_parser.py          Inkrement 1: components.xml -> FramePieceOut
    article_matching.py    Inkrement 2: gruppering + handelslängder
    cutting_optimizer.py   Inkrement 3: FFD-kapoptimering + inköpsunderlag
    csv_export.py          Inkrement 3: CSV-export av underlag och kaplista
    project_data.py        Cachad inläsning (filerna parsas en gång per process)
tests/                   pytest, ett testfilnamn per router
```

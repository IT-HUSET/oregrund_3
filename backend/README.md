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

Boilerplate-läge: alla endpoints svarar med fixture-data (`app/services/fixtures.py`), inte
riktig parsning/optimering. Se `app/services/{xml_parser,article_matching,cutting_optimizer}.py`
för stubbarna som ska fyllas i per inkrement, `../docs/plan.md`.

## Struktur

```
app/
  main.py               FastAPI-app, CORS, routrar
  config.py             Sökvägar (data/), KERF_MM
  models.py             Pydantic-scheman -- API-kontraktet
  routers/               GET-endpoints, tunna, anropar services/
  services/
    fixtures.py           Mock-/fixturdata (boilerplate-läge)
    xml_parser.py          Inkrement 1: components.xml -> FramePieceOut
    article_matching.py    Inkrement 2: gruppering + handelslängder
    cutting_optimizer.py   Inkrement 3: FFD-kapoptimering + inköpsunderlag
tests/                   pytest, ett testfilnamn per router
```

"""FastAPI-app. Kör: uvicorn app.main:app --reload --port 8000 (i backend/)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import bom, purchase_order

app = FastAPI(
    title="Öregrund 3 -- Inköps- och spilloptimering (demo-API)",
    description="Se docs/api-contract.md för fullständigt kontrakt och docs/adr.md för arkitektur.",
    version="0.1.0",
)

# Vite dev-server, se frontend/vite.config.ts.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(bom.router)
app.include_router(purchase_order.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

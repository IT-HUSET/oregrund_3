"""FastAPI-app. Kör: uvicorn app.main:app --reload --port 8000 (i backend/)."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import bom, purchase_order
from app.services.article_matching import get_trade_lengths_mm
from app.services.xml_parser import get_frame_pieces


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Läs in components.xml + handelslängder vid start (docs/adr.md skiss), inte på första
    requesten."""
    get_frame_pieces()
    get_trade_lengths_mm()
    yield


app = FastAPI(
    title="Öregrund 3 -- Inköps- och spilloptimering (demo-API)",
    description="Se docs/api-contract.md för fullständigt kontrakt och docs/adr.md för arkitektur.",
    version="0.1.0",
    lifespan=lifespan,
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

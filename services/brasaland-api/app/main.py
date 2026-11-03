"""Punto de entrada de la API: crea la aplicación y registra los routers de cada dominio."""

from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.domains.incidents.router import router as incidents_router

API_PREFIX = "/api/v1"

app = FastAPI(title="Brasaland API", version="0.1.0")
register_error_handlers(app)
app.include_router(incidents_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el servicio responde. Fuera de /api/v1 y sin autenticación (propuesta 3.4)."""
    return {"status": "ok"}

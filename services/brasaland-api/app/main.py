"""Punto de entrada de la API: crea la aplicación y registra los routers de cada dominio."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.errors import register_error_handlers
from app.domains.incidents.router import router as incidents_router
from app.domains.suppliers.dependencies import get_repository as get_supplier_repository
from app.domains.suppliers.router import router as suppliers_router
from app.domains.suppliers.seed import seed_if_empty

API_PREFIX = "/api/v1"

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # El directorio de proveedores nunca arranca vacío: si la tabla no tiene datos, se siembra.
    # Se respeta dependency_overrides para que las pruebas usen su propia base temporal.
    repository = app.dependency_overrides.get(get_supplier_repository, get_supplier_repository)()
    result = seed_if_empty(repository)
    if result is not None:
        logger.info("Directorio de proveedores sembrado: %s proveedores insertados.", result.inserted)
    yield


app = FastAPI(title="Brasaland API", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)
app.include_router(incidents_router, prefix=API_PREFIX)
app.include_router(suppliers_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Comprueba que el servicio responde. Fuera de /api/v1 y sin autenticación (propuesta 3.4)."""
    return {"status": "ok"}

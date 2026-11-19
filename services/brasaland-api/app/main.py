"""Punto de entrada de la API: crea la aplicación y registra los routers de cada dominio."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from app.core.config import API_PREFIX, frontend_origin, get_settings
from app.core.cors import PathScopedCORSMiddleware
from app.core.database import get_engine, init_db
from app.core.errors import register_error_handlers
from app.core.timing import register_timing_middleware
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.router import router as auth_router
from app.domains.incidents.manager_router import router as incident_manager_router
from app.domains.incidents.router import router as incidents_router
from app.domains.inventory.router import router as inventory_router
from app.domains.profiles.router import router as profiles_router
from app.domains.suppliers.dependencies import get_repository as get_supplier_repository
from app.domains.suppliers.router import router as suppliers_router
from app.domains.suppliers.seed import seed_if_empty
from app.domains.telemetry.router import router as telemetry_router
from app.domains.users.router import router as users_router

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Sin SECRET_KEY ni ACCESS_TOKEN_EXPIRE_MINUTES válidas, la API no arranca (ConfigError dice cuál falta).
    settings = get_settings()
    if not settings.email_enabled:
        # AUTH-03: sin clave de Resend la API funciona, pero no envía los enlaces de restablecimiento.
        logger.warning("Envío de correos desactivado: falta RESEND_API_KEY. /auth/forgot-password no enviará enlaces.")
    # Captura de telemetría: la URL del receptor se declara desde ya, aunque la API todavía no emite eventos.
    if settings.telemetry_endpoint:
        logger.info("Receptor de telemetría: %s (la API aún no envía eventos).", settings.telemetry_endpoint)

    # El directorio de proveedores nunca arranca vacío: si la tabla no tiene datos, se siembra.
    # Se respeta dependency_overrides para que las pruebas usen su propia base temporal.
    repository = app.dependency_overrides.get(get_supplier_repository, get_supplier_repository)()
    result = seed_if_empty(repository)
    if result is not None:
        logger.info("Directorio de proveedores sembrado: %s proveedores insertados.", result.inserted)

    # Inventario (Hito 5): sin DATABASE_URL la API no arranca. Crea en Supabase las tablas que falten.
    # Las pruebas sustituyen get_engine por un SQLite temporal.
    engine = app.dependency_overrides.get(get_engine, get_engine)()
    init_db(engine)
    yield


app = FastAPI(title="Brasaland API", version="0.1.0", lifespan=lifespan)
register_error_handlers(app)
# Caching: una línea de log por petición con su duración (logger "api.timing"), para medir antes de cachear.
register_timing_middleware(app)
# Rutas con datos sensibles: todas exigen un token válido (AUTH-01). Sin token, 401.
PROTECTED = [Depends(get_current_user)]
app.include_router(incidents_router, prefix=API_PREFIX, dependencies=PROTECTED)
# Gestor de incidencias centralizado: mismo prefijo /incidents que el analizador del CSV.
app.include_router(incident_manager_router, prefix=API_PREFIX, dependencies=PROTECTED)
app.include_router(suppliers_router, prefix=API_PREFIX, dependencies=PROTECTED)
# Inventario (Hito 5): APIRouter con prefijo /inventory, datos en Supabase. Todas sus rutas exigen token.
app.include_router(inventory_router, prefix=API_PREFIX, dependencies=PROTECTED)
# Autenticación (AUTH-01): login, usuarios (solo credenciales) y perfiles. AUTH-03 añade a /auth el
# restablecimiento (público) y el cambio (protegido) de contraseña.
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(profiles_router, prefix=API_PREFIX)
# Telemetría (fase de captura): receptor provisional POST /telemetry/events, fuera de /api/v1 y público,
# como /health. El navegador lo llama directamente (también con sendBeacon), así que es la única ruta
# con CORS, y solo para el origen del backoffice.
app.include_router(telemetry_router)
app.add_middleware(
    PathScopedCORSMiddleware,
    path_prefix=telemetry_router.prefix,
    allow_origins=[frontend_origin()],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class HealthResponse(BaseModel):
    """Respuesta de GET /health. Solo el estado: ni versión, ni dependencias, ni datos de la base."""

    status: Literal["ok"] = Field(description='Siempre "ok" si el servicio responde')


@app.get("/health", tags=["health"], response_model=HealthResponse)
def health() -> HealthResponse:
    """Comprueba que el servicio responde. Fuera de /api/v1 y pública: no expone datos (propuesta 3.4)."""
    return HealthResponse(status="ok")
